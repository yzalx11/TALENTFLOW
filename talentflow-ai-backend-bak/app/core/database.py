from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Async engine — FastAPI 路由用
ASYNC_URL = settings.SQLALCHEMY_DATABASE_URL.replace("mysql+pymysql://", "mysql+aiomysql://")
engine = create_async_engine(ASYNC_URL, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine — Celery Worker / 同步代码用
sync_engine = create_engine(settings.SQLALCHEMY_DATABASE_URL, echo=False)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine, class_=Session)


async def create_db_and_tables():
    from app import models
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    print("数据库表已检查/创建完成")


async def get_db():
    async with SessionLocal() as db:
        yield db


async def get_session():
    async with SessionLocal() as session:
        yield session
