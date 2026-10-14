import os

from sqlmodel import Session, SQLModel, create_engine

# Defaults to a local SQLite file; override with DATABASE_URL (e.g. for tests or Postgres).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///manga.db")

# SQLite connections are bound to the creating thread by default; FastAPI serves
# requests from a thread pool, so that check has to be disabled for SQLite.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
