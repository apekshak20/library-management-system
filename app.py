import click
from flask import Flask

from config import Config
from extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Connect the extensions to this app
    db.init_app(app)
    login_manager.init_app(app)

    # Import models so SQLAlchemy knows about the tables
    import models  # noqa: F401

    @app.route("/")
    def home():
        return (
            "<h1>Library Management System</h1>"
            "<p>Flask is running successfully ✅</p>"
        )

    # Custom terminal command: flask init-db
    @app.cli.command("init-db")
    def init_db():
        """Create all database tables in Supabase."""
        db.create_all()
        click.echo("Database tables created ✅")

    return app


# Gunicorn on Render will look for this "app" object
app = create_app()


if __name__ == "__main__":
    # Port 5001 because macOS uses port 5000 for AirPlay
    app.run(debug=True, port=5001)