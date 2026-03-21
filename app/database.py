from sqlmodel import Session, SQLModel, create_engine
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL
ENABLE_ANALYTICS = settings.ENABLE_ANALYTICS

engine = None
if ENABLE_ANALYTICS and DATABASE_URL:
    engine = create_engine(DATABASE_URL)

def create_db_and_tables():
    if engine is None:
        return
    SQLModel.metadata.create_all(engine)

def get_session():
    if engine is None:
        raise RuntimeError("Database engine is not initialized. Check ENABLE_ANALYTICS and DATABASE_URL.")
    with Session(engine) as session:
        yield session