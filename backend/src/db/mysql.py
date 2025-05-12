from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import global_config

SQLALCHEMY_DATABASE_URL = f"""mysql+pymysql://{global_config.MYSQL_USER}:{global_config.MYSQL_PASSWORD}@{global_config.MYSQL_HOST}:{global_config.MYSQL_PORT}/{global_config.MYSQL_DB}"""

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