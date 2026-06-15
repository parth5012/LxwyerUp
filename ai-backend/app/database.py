from sqlmodel import SQLModel, create_engine, Session
from config import settings

# For SQLite, we need connect_args={"check_same_thread": False}
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, echo=settings.DEBUG)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_db():
    with Session(engine) as session:
        yield session
