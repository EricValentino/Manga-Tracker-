from sqlmodel import create_engine, SQLModel 

sqlite_filename = "manga.db" 
engine = create_engine(f"sqlite:///{sqlite_filename}")

def create_db_and_tables(): 
    SQLModel.metadata.create_all(engine) 
