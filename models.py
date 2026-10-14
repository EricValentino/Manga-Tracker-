"""Database tables and request schemas.

Table models (``table=True``) describe what is stored. Request bodies use separate,
non-table models because SQLModel skips validation on table models; validating at
the edge keeps bad input (e.g. a rating of 50) out of the database.
"""

from typing import Literal

from sqlmodel import Field, SQLModel

ReadingStatus = Literal["reading", "completed", "plan to read"]


# ---------- Tables ----------


class Manga(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    genre: str
    total_chapters: int | None = None
    cover_image: str | None = None
    average_score: int | None = None


class ReadingProgress(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    chapter: int
    status: str
    rating: int | None = None
    # One progress record per saved manga.
    manga_id: int = Field(foreign_key="manga.id", unique=True, index=True)


class Anime(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    genre: str
    total_episodes: int | None = None
    cover_image: str | None = None
    average_score: int | None = None


# ---------- Request schemas ----------


class MangaCreate(SQLModel):
    title: str = Field(min_length=1, max_length=300)
    genre: str = Field(default="", max_length=300)
    total_chapters: int | None = Field(default=None, ge=0)
    cover_image: str | None = Field(default=None, max_length=2048)
    average_score: int | None = Field(default=None, ge=0, le=100)


class MangaUpdate(SQLModel):
    """Only these fields may be patched; ``id`` and unknown keys are rejected/ignored."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    genre: str | None = Field(default=None, max_length=300)
    total_chapters: int | None = Field(default=None, ge=0)
    cover_image: str | None = Field(default=None, max_length=2048)
    average_score: int | None = Field(default=None, ge=0, le=100)


class AnimeCreate(SQLModel):
    title: str = Field(min_length=1, max_length=300)
    genre: str = Field(default="", max_length=300)
    total_episodes: int | None = Field(default=None, ge=0)
    cover_image: str | None = Field(default=None, max_length=2048)
    average_score: int | None = Field(default=None, ge=0, le=100)


class ProgressCreate(SQLModel):
    manga_id: int
    chapter: int = Field(default=0, ge=0)
    status: ReadingStatus = "reading"
    rating: int | None = Field(default=None, ge=1, le=10)


class ProgressUpdate(SQLModel):
    chapter: int | None = Field(default=None, ge=0)
    status: ReadingStatus | None = None
    rating: int | None = Field(default=None, ge=1, le=10)
