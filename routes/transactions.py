from datetime import date, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Book, Student, Transaction, LOAN_PERIOD_DAYS

transactions_bp = Blueprint("transactions", __name__, url_prefix="/transactions")


def _render_issue(selected):
    """Show the issue form with the dropdown lists."""
    students = db.session.execute(
        db.select(Student).order_by(Student.name)
    ).scalars().all()
    # Only books that have at least one copy available
    books = db.session.execute(
        db.select(Book).where(Book.available_quantity > 0).order_by(Book.title)
    ).scalars().all()
    return render_template(
        "transactions/issue.html",
        students=students,
        books=books,
        selected=selected,
        min_date=date.today().isoformat(),
    )


@transactions_bp.route("/issue", methods=["GET", "POST"])
@login_required
def issue_book():
    today = date.today()
    selected = {
        "student_id": "",
        "book_id": "",
        "due_date": (today + timedelta(days=LOAN_PERIOD_DAYS)).isoformat(),
    }

    if request.method == "GET":
        return _render_issue(selected)

    # ----- POST: read the form -----
    selected["student_id"] = request.form.get("student_id", "")
    selected["book_id"] = request.form.get("book_id", "")
    selected["due_date"] = request.form.get("due_date", "")

    try:
        student_id = int(selected["student_id"])
        book_id = int(selected["book_id"])
    except ValueError:
        flash("Please select both a student and a book.", "danger")
        return _render_issue(selected)

    try:
        due_date = date.fromisoformat(selected["due_date"])
    except ValueError:
        flash("Please enter a valid due date.", "danger")
        return _render_issue(selected)

    if due_date < today:
        flash("Due date cannot be earlier than today.", "danger")
        return _render_issue(selected)

    student = db.session.get(Student, student_id)
    if student is None:
        flash("Selected student was not found.", "danger")
        return _render_issue(selected)

    # Lock this book's row until we commit, so two requests at the same
    # moment cannot both take the last copy.
    book = db.session.execute(
        db.select(Book).where(Book.id == book_id).with_for_update()
    ).scalar_one_or_none()

    if book is None:
        db.session.rollback()
        flash("Selected book was not found.", "danger")
        return _render_issue(selected)

    if book.available_quantity <= 0:
        db.session.rollback()
        flash(f"'{book.title}' is not available right now.", "danger")
        return _render_issue(selected)

    already_has = db.session.execute(
        db.select(Transaction).filter_by(
            student_id=student.id, book_id=book.id, status="issued"
        )
    ).first()
    if already_has:
        db.session.rollback()
        flash(
            f"{student.name} already has a copy of '{book.title}' and has not returned it.",
            "danger",
        )
        return _render_issue(selected)

    # Create the transaction AND reduce the quantity in one commit:
    # either both happen or neither does.
    transaction = Transaction(
        student_id=student.id,
        book_id=book.id,
        issue_date=today,
        due_date=due_date,
        status="issued",
    )
    book.available_quantity -= 1
    db.session.add(transaction)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Could not issue the book. Please try again.", "danger")
        return _render_issue(selected)

    flash(
        f"'{book.title}' issued to {student.name}. Due on {due_date.strftime('%d %b %Y')}.",
        "success",
    )
    return redirect(url_for("transactions.return_list"))


@transactions_bp.route("/return")
@login_required
def return_list():
    query = request.args.get("q", "").strip()

    stmt = (
        db.select(Transaction)
        .join(Transaction.student)
        .join(Transaction.book)
        .where(Transaction.status == "issued")
        .order_by(Transaction.due_date)
    )
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(
            db.or_(
                Student.name.ilike(pattern),
                Student.usn.ilike(pattern),
                Book.title.ilike(pattern),
                Book.isbn.ilike(pattern),
            )
        )

    transactions = db.session.execute(stmt).scalars().all()
    return render_template(
        "transactions/return.html",
        transactions=transactions,
        query=query,
        today=date.today(),
    )


@transactions_bp.route("/<int:transaction_id>/return", methods=["POST"])
@login_required
def return_book(transaction_id):
    # Lock the transaction row, so the same return cannot be processed twice
    transaction = db.session.execute(
        db.select(Transaction).where(Transaction.id == transaction_id).with_for_update()
    ).scalar_one_or_none()

    if transaction is None:
        db.session.rollback()
        abort(404)

    if transaction.status == "returned":
        db.session.rollback()
        flash("This transaction has already been returned.", "warning")
        return redirect(url_for("transactions.return_list"))

    book = db.session.execute(
        db.select(Book).where(Book.id == transaction.book_id).with_for_update()
    ).scalar_one()

    if book.available_quantity >= book.total_quantity:
        db.session.rollback()
        flash(
            "Cannot return: this book's available quantity is already at its total. "
            "Please check the book's quantity.",
            "danger",
        )
        return redirect(url_for("transactions.return_list"))

    today = date.today()
    title = book.title
    student_name = transaction.student.name
    days_late = (today - transaction.due_date).days

    transaction.status = "returned"
    transaction.return_date = today
    book.available_quantity += 1

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Could not record the return. Please try again.", "danger")
        return redirect(url_for("transactions.return_list"))

    if days_late > 0:
        flash(
            f"'{title}' returned by {student_name}, {days_late} day(s) late.",
            "warning",
        )
    else:
        flash(f"'{title}' returned by {student_name}.", "success")
    return redirect(url_for("transactions.return_list"))


@transactions_bp.route("/history")
@login_required
def history():
    query = request.args.get("q", "").strip()
    status = request.args.get("status", "all")
    page = request.args.get("page", 1, type=int)
    today = date.today()

    stmt = (
        db.select(Transaction)
        .join(Transaction.student)
        .join(Transaction.book)
        .order_by(Transaction.id.desc())
    )

    if status == "issued":
        stmt = stmt.where(Transaction.status == "issued")
    elif status == "returned":
        stmt = stmt.where(Transaction.status == "returned")
    elif status == "overdue":
        stmt = stmt.where(Transaction.status == "issued", Transaction.due_date < today)
    else:
        status = "all"

    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(
            db.or_(
                Student.name.ilike(pattern),
                Student.usn.ilike(pattern),
                Book.title.ilike(pattern),
                Book.author.ilike(pattern),
                Book.isbn.ilike(pattern),
            )
        )

    pagination = db.paginate(stmt, page=page, per_page=15, error_out=False)

    return render_template(
        "transactions/history.html",
        pagination=pagination,
        transactions=pagination.items,
        query=query,
        status=status,
        today=today,
    )