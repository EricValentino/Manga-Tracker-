from sqlmodel import SQLModel, Field 
from typing import Optional 

class Manga(SQLModel, table=True): 
    id: Optional[int] = Field(default=None, primary_key=True) 
    title: str 
    genre: str 
    total_chapters: Optional[int] = None 
    cover_image: Optional[str] = None
    average_score: Optional[int] = None



class ReadingProgress(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    chapter: int
    status: str 
    rating: Optional[int] = None 
    manga_id: Optional[int] = Field(default=None, foreign_key="manga.id")

class Anime(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    genre: str 
    total_episodes: Optional[int] = None
    cover_image: Optional[str] = None
    average_score: Optional[int] = None

class ProgressUpdate(SQLModel): 
    chapter: Optional[int] = None
    status: Optional[str] = None
    rating: Optional[int] = None