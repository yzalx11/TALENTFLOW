from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False}

engine = create_engine(settings.SQLALCHEMY_DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


def create_db_and_tables():
    from app import models
    SQLModel.metadata.create_all(engine)
    print("数据库表已检查/创建完成")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session():
    with Session(engine) as session:
        yield session
