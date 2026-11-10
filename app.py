from flask import Flask
from sqlalchemy import text

from config import Config
from extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Connect the extensions to this app
    db.init_app(app)
    login_manager.init_app(app)

    @app.route("/")
    def home():
        return (
            "<h1>Library Management System</h1>"
            "<p>Flask is running successfully ✅</p>"
            "<p><a href='/db-test'>Test database connection</a></p>"
        )

    # TEMPORARY route: we will delete it in the next stage
    @app.route("/db-test")
    def db_test():
        try:
            version = db.session.execute(text("SELECT version();")).scalar()
            return f"<h1>Database connected ✅</h1><p>{version}</p>"
        except Exception as error:
            app.logger.error("Database connection failed: %s", error)
            return (
                "<h1>Database connection failed ❌</h1>"
                "<p>Check the terminal for the full error message.</p>"
            ), 500

    return app


# Gunicorn on Render will look for this "app" object
app = create_app()


if __name__ == "__main__":
    # Port 5001 because macOS uses port 5000 for AirPlay
    app.run(debug=True, port=5001)