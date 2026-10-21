import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        port=os.getenv("POSTGRES_PORT"),
    )


# ==================================================
# MYSQL / SQLALCHEMY
# ==================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def get_mysql_url():
    mysql_url = os.getenv("MYSQL_DATABASE_URL")

    if mysql_url:
        return mysql_url

    mysql_user = os.getenv("MYSQL_USER", "actividad3")
    mysql_password = os.getenv("MYSQL_PASSWORD", "actividad3")
    mysql_host = os.getenv("MYSQL_HOST", "localhost")
    mysql_port = os.getenv("MYSQL_PORT", "3306")
    mysql_database = os.getenv("MYSQL_DATABASE", "actividad3")

    return (
        f"mysql+pymysql://{mysql_user}:{mysql_password}"
        f"@{mysql_host}:{mysql_port}/{mysql_database}"
    )


SQLALCHEMY_DATABASE_URL = get_mysql_url()

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
