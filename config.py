import os
from dotenv import load_dotenv

# Reads the .env file and loads its values as environment variables
load_dotenv()


def _get_database_url():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Check that your .env file exists "
            "and contains DATABASE_URL=..."
        )
    # Some providers give "postgres://", SQLAlchemy needs "postgresql://"
        # Force SQLAlchemy to use the psycopg2 driver we installed
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def _get_secret_key():
    key = os.environ.get("SECRET_KEY")
    if not key:
        raise RuntimeError(
            "SECRET_KEY is not set. Check that your .env file exists "
            "and contains SECRET_KEY=..."
        )
    return key


class Config:
    SECRET_KEY = _get_secret_key()
    SQLALCHEMY_DATABASE_URI = _get_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Keeps cloud database connections healthy
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,   # test a connection before using it
        "pool_recycle": 300,     # refresh connections every 5 minutes
    }