from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import global_config

SQLALCHEMY_DATABASE_URL = f"""postgresql+psycopg2://{global_config.DB_USER}:{global_config.DB_PASSWORD}@{global_config.DB_HOST}:{global_config.DB_PORT}/{global_config.DB_NAME}"""

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def get_db_session_local():
    """Function to get a database session for Celery tasks"""
    return SessionLocal()