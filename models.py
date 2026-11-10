from datetime import date, timedelta

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db, login_manager

LOAN_PERIOD_DAYS = 14


class Admin(UserMixin, db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        # Stores a one-way hash, never the real password
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Admin {self.username}>"


@login_manager.user_loader
def load_admin(admin_id):
    # Flask-Login calls this on every request to find the logged-in admin
    return db.session.get(Admin, int(admin_id))


class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    category = db.Column(db.String(100))
    total_quantity = db.Column(db.Integer, nullable=False, default=1)
    available_quantity = db.Column(db.Integer, nullable=False, default=1)

    transactions = db.relationship("Transaction", back_populates="book")

    __table_args__ = (
        db.CheckConstraint("total_quantity >= 0", name="ck_total_quantity_non_negative"),
        db.CheckConstraint("available_quantity >= 0", name="ck_available_non_negative"),
        db.CheckConstraint(
            "available_quantity <= total_quantity", name="ck_available_not_above_total"
        ),
    )

    @property
    def issued_quantity(self):
        return self.total_quantity - self.available_quantity

    def __repr__(self):
        return f"<Book {self.title}>"


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    usn = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    department = db.Column(db.String(100))

    transactions = db.relationship("Transaction", back_populates="student")

    def __repr__(self):
        return f"<Student {self.usn}>"


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    issue_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(
        db.Date,
        nullable=False,
        default=lambda: date.today() + timedelta(days=LOAN_PERIOD_DAYS),
    )
    return_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(10), nullable=False, default="issued")

    student = db.relationship("Student", back_populates="transactions")
    book = db.relationship("Book", back_populates="transactions")

    __table_args__ = (
        db.CheckConstraint("status IN ('issued', 'returned')", name="ck_status_valid"),
    )

    def __repr__(self):
        return f"<Transaction {self.id} {self.status}>"