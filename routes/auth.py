from urllib.parse import urlparse

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import Admin

auth_bp = Blueprint("auth", __name__)


def _is_safe_redirect(target):
    """Only allow redirects to pages inside our own site."""
    if not target:
        return False
    parsed = urlparse(target)
    return parsed.scheme == "" and parsed.netloc == "" and target.startswith("/")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admin = db.session.execute(
            db.select(Admin).filter_by(username=username)
        ).scalar_one_or_none()

        if admin and admin.check_password(password):
            login_user(admin)
            flash("Logged in successfully.", "success")
            next_page = request.args.get("next")
            if _is_safe_redirect(next_page):
                return redirect(next_page)
            return redirect(url_for("dashboard.index"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))