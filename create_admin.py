import getpass

from app import app
from extensions import db
from models import Admin


def main():
    username = input("Choose an admin username: ").strip()
    if not username:
        print("Username cannot be empty.")
        return

    password = getpass.getpass("Choose a password (min 8 characters): ")
    confirm = getpass.getpass("Confirm password: ")

    if len(password) < 8:
        print("Password must be at least 8 characters.")
        return
    if password != confirm:
        print("Passwords do not match.")
        return

    with app.app_context():
        existing = db.session.execute(
            db.select(Admin).filter_by(username=username)
        ).scalar_one_or_none()
        if existing:
            print(f"Admin '{username}' already exists.")
            return

        admin = Admin(username=username)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin '{username}' created successfully ✅")


if __name__ == "__main__":
    main()