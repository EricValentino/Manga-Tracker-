from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

import anilist
import recommendations as recs_service
from database import create_db_and_tables, get_session
from models import (
    Anime,
    AnimeCreate,
    Manga,
    MangaCreate,
    MangaUpdate,
    ProgressCreate,
    ProgressUpdate,
    ReadingProgress,
)

load_dotenv()

STATIC_DIR = Path(__file__).parent / "static"
SortOption = Literal["TRENDING_DESC", "SCORE_DESC", "POPULARITY_DESC"]
MediaType = Literal["MANGA", "ANIME"]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="AniTracker API", lifespan=lifespan)


def _upstream_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=502, detail=f"Catalog service unavailable: {exc}")


def _get_or_404(session: Session, model, item_id: int, label: str):
    item = session.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return item


# ---------- Health ----------


@app.get("/")
def read_root():
    return {"message": "Manga tracker API is alive"}


# ---------- Manga library ----------


@app.get("/manga", response_model=list[Manga])
def list_manga(session: Session = Depends(get_session)):
    return session.exec(select(Manga)).all()


@app.post("/manga", response_model=Manga, status_code=201)
def create_manga(payload: MangaCreate, session: Session = Depends(get_session)):
    manga = Manga.model_validate(payload)
    session.add(manga)
    session.commit()
    session.refresh(manga)
    return manga


@app.patch("/manga/{manga_id}", response_model=Manga)
def update_manga(manga_id: int, updates: MangaUpdate, session: Session = Depends(get_session)):
    manga = _get_or_404(session, Manga, manga_id, "Manga")
    manga.sqlmodel_update(updates.model_dump(exclude_unset=True))
    session.add(manga)
    session.commit()
    session.refresh(manga)
    return manga


@app.delete("/manga/{manga_id}")
def delete_manga(manga_id: int, session: Session = Depends(get_session)):
    manga = _get_or_404(session, Manga, manga_id, "Manga")
    # Remove the dependent progress record first so no orphan rows are left behind.
    for progress in session.exec(
        select(ReadingProgress).where(ReadingProgress.manga_id == manga_id)
    ).all():
        session.delete(progress)
    session.delete(manga)
    session.commit()
    return {"message": "Manga deleted"}


# ---------- Reading progress ----------


@app.get("/progress", response_model=list[ReadingProgress])
def list_progress(session: Session = Depends(get_session)):
    return session.exec(select(ReadingProgress)).all()


@app.post("/progress", response_model=ReadingProgress, status_code=201)
def create_progress(payload: ProgressCreate, session: Session = Depends(get_session)):
    _get_or_404(session, Manga, payload.manga_id, "Manga")
    existing = session.exec(
        select(ReadingProgress).where(ReadingProgress.manga_id == payload.manga_id)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Progress already exists for this manga (id {existing.id}); use PATCH",
        )
    progress = ReadingProgress.model_validate(payload)
    session.add(progress)
    session.commit()
    session.refresh(progress)
    return progress


@app.patch("/progress/{progress_id}", response_model=ReadingProgress)
def update_progress(
    progress_id: int, updates: ProgressUpdate, session: Session = Depends(get_session)
):
    progress = _get_or_404(session, ReadingProgress, progress_id, "Progress")
    progress.sqlmodel_update(updates.model_dump(exclude_unset=True))
    session.add(progress)
    session.commit()
    session.refresh(progress)
    return progress


@app.delete("/progress/{progress_id}")
def delete_progress(progress_id: int, session: Session = Depends(get_session)):
    progress = _get_or_404(session, ReadingProgress, progress_id, "Progress")
    session.delete(progress)
    session.commit()
    return {"message": "Progress deleted"}


# ---------- Anime library ----------


@app.get("/anime", response_model=list[Anime])
def list_anime(session: Session = Depends(get_session)):
    return session.exec(select(Anime)).all()


@app.post("/anime", response_model=Anime, status_code=201)
def create_anime(payload: AnimeCreate, session: Session = Depends(get_session)):
    anime = Anime.model_validate(payload)
    session.add(anime)
    session.commit()
    session.refresh(anime)
    return anime


# ---------- Catalog (AniList proxy) ----------


def _search(title: str, media_type: str):
    try:
        result = anilist.search_media(title, media_type)
    except anilist.AniListError as exc:
        raise _upstream_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail=f"No {media_type.lower()} found for '{title}'")
    return result


@app.get("/search")
def search(title: str = Query(min_length=1, max_length=200)):
    return _search(title, "MANGA")


@app.get("/search-anime")
def search_anime(title: str = Query(min_length=1, max_length=200)):
    return _search(title, "ANIME")


@app.get("/discover")
def discover_manga(
    sort: SortOption, country: str | None = Query(default=None, pattern="^[A-Z]{2}$")
):
    try:
        return anilist.get_manga_list(sort, country)
    except anilist.AniListError as exc:
        raise _upstream_error(exc) from exc


@app.get("/discover-anime")
def discover_anime(sort: SortOption):
    try:
        return anilist.get_anime_list(sort)
    except anilist.AniListError as exc:
        raise _upstream_error(exc) from exc


@app.get("/details")
def details(id: int, type: MediaType):
    try:
        result = anilist.get_details(id, type)
    except anilist.AniListError as exc:
        raise _upstream_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Title not found")
    return result


# ---------- AI recommendations ----------


@app.get("/recommendations")
def recommendations(session: Session = Depends(get_session)):
    manga_list = session.exec(select(Manga)).all()
    try:
        recs = recs_service.get_recommendations(manga_list)
    except recs_service.RecommendationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Enrich each suggestion with real cover art. A failed lookup only drops the
    # image; it should not fail the whole response.
    for rec in recs:
        try:
            match = anilist.search_manga(rec["title"])
        except anilist.AniListError:
            match = None
        rec["cover_image"] = ((match or {}).get("coverImage") or {}).get("large")
    return recs


# ---------- Frontend ----------

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/app", include_in_schema=False)
def serve_frontend():
    return FileResponse(STATIC_DIR / "index.html")
