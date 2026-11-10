from flask import Blueprint, render_template
from flask_login import login_required

from extensions import db
from models import Book, Student, Transaction

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    # Number of different titles
    total_titles = db.session.execute(
        db.select(db.func.count(Book.id))
    ).scalar_one()

    # Number of copies (sum of quantities); coalesce turns "no rows" into 0
    total_copies = db.session.execute(
        db.select(db.func.coalesce(db.func.sum(Book.total_quantity), 0))
    ).scalar_one()

    available_copies = db.session.execute(
        db.select(db.func.coalesce(db.func.sum(Book.available_quantity), 0))
    ).scalar_one()

    total_students = db.session.execute(
        db.select(db.func.count(Student.id))
    ).scalar_one()

    currently_issued = db.session.execute(
        db.select(db.func.count(Transaction.id)).where(Transaction.status == "issued")
    ).scalar_one()

    recent = db.session.execute(
        db.select(Transaction)
        .order_by(Transaction.id.desc())
        .limit(10)
    ).scalars().all()

    return render_template(
        "dashboard.html",
        total_titles=total_titles,
        total_copies=total_copies,
        available_copies=available_copies,
        total_students=total_students,
        currently_issued=currently_issued,
        recent=recent,
    )