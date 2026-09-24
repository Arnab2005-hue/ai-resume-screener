
import os

from sqlalchemy import (
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import (
    sessionmaker,
)
from sqlalchemy.exc import (
    SQLAlchemyError,
)


def normalize_database_url(
    url: str,
) -> str:

    url = url.strip()

    if url.startswith(
        "postgres://"
    ):

        url = (
            "postgresql+psycopg://"
            + url[len("postgres://"):]
        )

    elif url.startswith(
        "postgresql://"
    ):

        url = (
            "postgresql+psycopg://"
            + url[len("postgresql://"):]
        )

    elif not url.startswith(
        "postgresql+psycopg://"
    ):

        raise ValueError(
            "DATABASE_URL must be a PostgreSQL connection URL."
        )

    if "sslmode=" not in url.lower():

        separator = (
            "&"
            if "?" in url
            else "?"
        )

        url += (
            separator
            + "sslmode=require"
        )

    return url


DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

engine = None
SessionLocal = None


if DATABASE_URL:

    normalized_url = (
        normalize_database_url(
            DATABASE_URL
        )
    )

    engine = create_engine(
        normalized_url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=0,
        pool_recycle=1800,
        future=True,
    )

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def get_db():

    if SessionLocal is None:

        raise RuntimeError(
            "DATABASE_URL is not configured."
        )

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()


def check_database_connection():

    if engine is None:

        return {
            "configured": False,
            "connected": False,
            "status": "DATABASE_URL_NOT_CONFIGURED",
            "tables": [],
        }

    try:

        with engine.connect() as connection:

            connection.execute(
                text("SELECT 1")
            )

            inspector = inspect(
                connection
            )

            tables = sorted(
                inspector.get_table_names(
                    schema="public"
                )
            )

        required_tables = {
            "jobs",
            "candidates",
            "screening_results",
            "screening_skills",
        }

        missing_tables = sorted(
            required_tables
            - set(tables)
        )

        return {
            "configured": True,
            "connected": True,
            "status": (
                "CONNECTED"
                if not missing_tables
                else "TABLES_MISSING"
            ),
            "tables": tables,
            "missing_required_tables": missing_tables,
        }

    except SQLAlchemyError as exc:

        return {
            "configured": True,
            "connected": False,
            "status": "CONNECTION_FAILED",
            "tables": [],
            "error": str(exc),
        }
