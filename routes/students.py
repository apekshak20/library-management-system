import re

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Student, Transaction

students_bp = Blueprint("students", __name__, url_prefix="/students")

# Simple email check: something@something.something
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _read_form():
    """Read and clean the student form. Returns (data, error_message)."""
    data = {
        "name": request.form.get("name", "").strip(),
        "usn": request.form.get("usn", "").strip().upper(),
        "email": request.form.get("email", "").strip().lower(),
        "department": request.form.get("department", "").strip(),
    }

    if not data["name"] or not data["usn"] or not data["email"]:
        return data, "Name, USN and email are required."

    if not EMAIL_PATTERN.match(data["email"]):
        return data, "Please enter a valid email address."

    return data, None


@students_bp.route("/")
@login_required
def list_students():
    query = request.args.get("q", "").strip()

    stmt = db.select(Student).order_by(Student.name)
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(
            db.or_(
                Student.name.ilike(pattern),
                Student.usn.ilike(pattern),
                Student.email.ilike(pattern),
                Student.department.ilike(pattern),
            )
        )

    students = db.session.execute(stmt).scalars().all()
    return render_template("students/list.html", students=students, query=query)


@students_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_student():
    if request.method == "POST":
        data, error = _read_form()
        if error:
            flash(error, "danger")
            return render_template("students/form.html", student=data, mode="add")

        if db.session.execute(
            db.select(Student).filter_by(usn=data["usn"])
        ).scalar_one_or_none():
            flash("A student with this USN already exists.", "danger")
            return render_template("students/form.html", student=data, mode="add")

        if db.session.execute(
            db.select(Student).filter_by(email=data["email"])
        ).scalar_one_or_none():
            flash("A student with this email already exists.", "danger")
            return render_template("students/form.html", student=data, mode="add")

        student = Student(
            name=data["name"],
            usn=data["usn"],
            email=data["email"],
            department=data["department"] or None,
        )
        db.session.add(student)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Could not save the student. Check the details and try again.", "danger")
            return render_template("students/form.html", student=data, mode="add")

        flash(f"Student '{student.name}' registered successfully.", "success")
        return redirect(url_for("students.list_students"))

    return render_template("students/form.html", student=None, mode="add")


@students_bp.route("/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    student = db.get_or_404(Student, student_id)

    if request.method == "POST":
        data, error = _read_form()
        if error:
            flash(error, "danger")
            data["id"] = student.id
            return render_template("students/form.html", student=data, mode="edit")

        if db.session.execute(
            db.select(Student).where(Student.usn == data["usn"], Student.id != student.id)
        ).scalar_one_or_none():
            flash("Another student already uses this USN.", "danger")
            data["id"] = student.id
            return render_template("students/form.html", student=data, mode="edit")

        if db.session.execute(
            db.select(Student).where(Student.email == data["email"], Student.id != student.id)
        ).scalar_one_or_none():
            flash("Another student already uses this email.", "danger")
            data["id"] = student.id
            return render_template("students/form.html", student=data, mode="edit")

        student.name = data["name"]
        student.usn = data["usn"]
        student.email = data["email"]
        student.department = data["department"] or None

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Could not update the student. Check the details and try again.", "danger")
            data["id"] = student.id
            return render_template("students/form.html", student=data, mode="edit")

        flash(f"Student '{student.name}' updated successfully.", "success")
        return redirect(url_for("students.list_students"))

    return render_template("students/form.html", student=student, mode="edit")


@students_bp.route("/<int:student_id>/delete", methods=["POST"])
@login_required
def delete_student(student_id):
    student = db.get_or_404(Student, student_id)

    # Block deleting a student who still holds unreturned books
    active = db.session.execute(
        db.select(Transaction).filter_by(student_id=student.id, status="issued")
    ).first()
    if active:
        flash(
            f"Cannot delete '{student.name}': they have books that are not returned yet.",
            "danger",
        )
        return redirect(url_for("students.list_students"))

    # Block deleting a student who has history (keeps records consistent)
    has_history = db.session.execute(
        db.select(Transaction).filter_by(student_id=student.id)
    ).first()
    if has_history:
        flash(
            f"Cannot delete '{student.name}': they have transaction history.",
            "warning",
        )
        return redirect(url_for("students.list_students"))

    name = student.name
    db.session.delete(student)
    db.session.commit()
    flash(f"Student '{name}' deleted.", "success")
    return redirect(url_for("students.list_students"))