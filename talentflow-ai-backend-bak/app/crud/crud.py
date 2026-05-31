from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import user as user_model
from app import schemas
from app.core import security


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[user_model.User]:
    result = await db.execute(select(user_model.User).where(user_model.User.username == username))
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[user_model.User]:
    result = await db.execute(select(user_model.User).where(user_model.User.id == user_id))
    return result.scalars().first()


async def create_user(db: AsyncSession, user_in: schemas.UserCreate) -> user_model.User:
    hashed_password = security.get_password_hash(user_in.password)
    db_user = user_model.User(
        username=user_in.username,
        email=user_in.email or f"{user_in.username}@talentflow.ai",
        password=hashed_password,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user
