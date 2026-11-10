from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Book, Transaction

books_bp = Blueprint("books", __name__, url_prefix="/books")


def _read_form():
    """Read and clean the book form. Returns (data, error_message)."""
    data = {
        "title": request.form.get("title", "").strip(),
        "author": request.form.get("author", "").strip(),
        "isbn": request.form.get("isbn", "").strip(),
        "category": request.form.get("category", "").strip(),
        "total_quantity": request.form.get("total_quantity", "").strip(),
    }

    if not data["title"] or not data["author"] or not data["isbn"]:
        return data, "Title, author and ISBN are required."

    try:
        data["total_quantity"] = int(data["total_quantity"])
    except ValueError:
        return data, "Total quantity must be a whole number."

    if data["total_quantity"] < 0:
        return data, "Total quantity cannot be negative."

    return data, None


@books_bp.route("/")
@login_required
def list_books():
    query = request.args.get("q", "").strip()

    stmt = db.select(Book).order_by(Book.title)
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(
            db.or_(
                Book.title.ilike(pattern),
                Book.author.ilike(pattern),
                Book.isbn.ilike(pattern),
            )
        )

    books = db.session.execute(stmt).scalars().all()
    return render_template("books/list.html", books=books, query=query)


@books_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_book():
    if request.method == "POST":
        data, error = _read_form()
        if error:
            flash(error, "danger")
            return render_template("books/form.html", book=data, mode="add")

        existing = db.session.execute(
            db.select(Book).filter_by(isbn=data["isbn"])
        ).scalar_one_or_none()
        if existing:
            flash("A book with this ISBN already exists.", "danger")
            return render_template("books/form.html", book=data, mode="add")

        book = Book(
            title=data["title"],
            author=data["author"],
            isbn=data["isbn"],
            category=data["category"] or None,
            total_quantity=data["total_quantity"],
            available_quantity=data["total_quantity"],  # all copies start available
        )
        db.session.add(book)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Could not save the book. Check the details and try again.", "danger")
            return render_template("books/form.html", book=data, mode="add")

        flash(f"Book '{book.title}' added successfully.", "success")
        return redirect(url_for("books.list_books"))

    return render_template("books/form.html", book=None, mode="add")


@books_bp.route("/<int:book_id>/edit", methods=["GET", "POST"])
@login_required
def edit_book(book_id):
    book = db.get_or_404(Book, book_id)

    if request.method == "POST":
        data, error = _read_form()
        if error:
            flash(error, "danger")
            data["id"] = book.id
            return render_template("books/form.html", book=data, mode="edit")

        # ISBN must stay unique (ignore this same book)
        duplicate = db.session.execute(
            db.select(Book).where(Book.isbn == data["isbn"], Book.id != book.id)
        ).scalar_one_or_none()
        if duplicate:
            flash("Another book already uses this ISBN.", "danger")
            data["id"] = book.id
            return render_template("books/form.html", book=data, mode="edit")

        # New total can't be lower than the copies currently issued
        issued = book.total_quantity - book.available_quantity
        if data["total_quantity"] < issued:
            flash(
                f"Total quantity cannot be less than the {issued} copies "
                "currently issued.",
                "danger",
            )
            data["id"] = book.id
            return render_template("books/form.html", book=data, mode="edit")

        book.title = data["title"]
        book.author = data["author"]
        book.isbn = data["isbn"]
        book.category = data["category"] or None
        book.total_quantity = data["total_quantity"]
        # Keep the issued count the same, so availability stays correct
        book.available_quantity = data["total_quantity"] - issued

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Could not update the book. Check the details and try again.", "danger")
            data["id"] = book.id
            return render_template("books/form.html", book=data, mode="edit")

        flash(f"Book '{book.title}' updated successfully.", "success")
        return redirect(url_for("books.list_books"))

    return render_template("books/form.html", book=book, mode="edit")


@books_bp.route("/<int:book_id>/delete", methods=["POST"])
@login_required
def delete_book(book_id):
    book = db.get_or_404(Book, book_id)

    # Block deleting a book that still has unreturned copies
    active = db.session.execute(
        db.select(Transaction).filter_by(book_id=book.id, status="issued")
    ).first()
    if active:
        flash(
            f"Cannot delete '{book.title}': some copies are currently issued.",
            "danger",
        )
        return redirect(url_for("books.list_books"))

    # Block deleting a book that has history (keeps records consistent)
    has_history = db.session.execute(
        db.select(Transaction).filter_by(book_id=book.id)
    ).first()
    if has_history:
        flash(
            f"Cannot delete '{book.title}': it has transaction history. "
            "Set its quantity instead.",
            "warning",
        )
        return redirect(url_for("books.list_books"))

    title = book.title
    db.session.delete(book)
    db.session.commit()
    flash(f"Book '{title}' deleted.", "success")
    return redirect(url_for("books.list_books"))