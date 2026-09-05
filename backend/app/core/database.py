from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker

from app.core.config import Config

db_url = Config().database_url
if db_url.startswith(("postgres://", "postgresql://")):
    db_url = "postgresql+psycopg://" + db_url.split("://", 1)[1]

engine = create_engine(db_url, pool_pre_ping=True)

class Base(DeclarativeBase):
    pass

SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
