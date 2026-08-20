import os

from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from recommendations import get_recommendations

from database import create_db_and_tables, engine
from models import Anime, Manga, ReadingProgress, ProgressUpdate, Anime 
from anilist import search_manga
from anilist import search_manga, get_manga_list,search_anime, get_anime_list, get_details


load_dotenv() 
app = FastAPI() 

def get_session():
    with Session(engine) as session: 
        yield session 

@app.get("/manga")
def manga_saver(session: Session = Depends(get_session)): 
    manga_list = session.exec(select(Manga)).all()
    return manga_list 

@app.post("/manga")
def create_manga(manga: Manga, session: Session = Depends(get_session)):
    manga.id = None
    session.add(manga)
    session.commit()
    session.refresh(manga)
    return manga

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/") 
def read_root(): 
    return {"message": "Manga tracker API is alive"}

@app.post("/progress")
def create_progress(progress: ReadingProgress, session: Session = Depends(get_session)):
    progress.id = None
    session.add(progress) 
    session.commit()
    session.refresh(progress) 
    return progress

@app.get("/progress")
def get_all_progress(session: Session = Depends(get_session)): 
    progress_list = session.exec(select(ReadingProgress)).all()
    return progress_list

@app.delete("/manga/{manga_id}")
def delete_manga(manga_id: int, session: Session = Depends(get_session)):
    manga = session.get(Manga, manga_id)
    if not manga:
        return {"error": "Manga not found"}
    session.delete(manga)
    session.commit()
    return {"message": "Manga deleted"}

@app.delete("/progress/{progress_id}")
def delete_progress(progress_id: int, session: Session = Depends(get_session)):
    progress = session.get(ReadingProgress, progress_id)
    if not progress:
        return {"error": "Progress not found"}
    session.delete(progress)
    session.commit()
    return {"message": "Progress deleted"}

@app.patch("/progress/{progress_id}")
def update_progress(progress_id: int, updates: ProgressUpdate, session: Session = Depends(get_session)):
    progress = session.get(ReadingProgress, progress_id)
    if not progress: 
        return{"error": "Progress not found"}

    update_data = updates.dict(exclude_unset=True) 
    for key, value in update_data.items(): 
        setattr(progress, key, value)

    session.add(progress)
    session.commit() 
    session.refresh(progress)
    return progress 

@app.patch("/manga/{manga_id}")
def update_manga(manga_id: int, updates: dict, session: Session = Depends(get_session)):
    manga = session.get(Manga, manga_id)
    if not manga:
        return {"error": "Manga not found"}

    for key, value in updates.items():
        setattr(manga, key, value)

    session.add(manga)
    session.commit()
    session.refresh(manga)
    return manga

@app.get("/search")
def search(title: str): 
    return search_manga(title)


app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/app")
def serve_frontend():
    return FileResponse("static/index.html")

@app.get("/recommendations")
def recommendations(session: Session = Depends(get_session)):
    manga_list = session.exec(select(Manga)).all()
    recs = get_recommendations(manga_list)

    for rec in recs: 
        result = search_manga(rec["title"])
        rec["cover_image"] = result["coverImage"]["large"] if result else None 

    return recs

@app.get("/discover")
def discover(sort: str, country: str = None):
    allowed = ["TRENDING_DESC", "SCORE_DESC", "POPULARITY_DESC"]
    if sort not in allowed:
        return {"error": "Invalid sort option"}
    return get_manga_list(sort, country)

@app.post("/anime")
def create_anime(anime: Anime, session: Session = Depends(get_session)):
    anime.id = None 
    session.add(anime) 
    session.commit() 
    session.refresh(anime) 
    return anime 

@app.get("/anime")
def anime_saver(session: Session = Depends(get_session)):
    anime_list = session.exec(select(Anime)).all()
    return anime_list 

@app.get("/search-anime")
def search_anime_route(title: str):
    return search_anime(title)

@app.get("/discover-anime")
def discover(sort: str,):
    allowed = ["TRENDING_DESC", "SCORE_DESC", "POPULARITY_DESC"]
    if sort not in allowed:
        return {"error": "Invalid sort option"}
    return get_anime_list(sort)

@app.get("/details")
def details(id: int, type: str):
    return get_details(id, type)