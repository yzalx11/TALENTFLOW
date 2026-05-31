# app/api/v1/admin/user_manager.py
"""管理员端 — 用户管理"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional

from app.models.user import User
from app.core.database import get_db
from app.core.security import get_password_hash
from app.core.deps import get_current_active_admin

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-Users"])


# ---- 用户列表 ----
@router.get("/users", response_model=List[dict])
async def list_users(
    skip: int = 0, limit: int = 100,
    keyword: Optional[str] = Query(None), role: Optional[int] = Query(None),
    current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db),
):
    conditions = []
    if keyword: conditions.append(or_(User.username.like(f"%{keyword}%"), User.full_name.like(f"%{keyword}%")))
    if role is not None: conditions.append(User.role == role)
    user_query = await db.execute(select(User).where(*conditions).offset(skip).limit(limit))
    users = user_query.scalars().all()
    return [{"id": u.id, "username": u.username, "email": u.email, "full_name": u.full_name,
             "role": u.role, "is_active": u.is_active, "created_at": str(u.created_at) if u.created_at else None}
            for u in users]


# ---- 用户详情 ----
@router.get("/users/{user_id}")
async def get_user(user_id: int, current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db)):
    user_query = await db.execute(select(User).where(User.id == user_id))
    user = user_query.scalar()
    if not user: raise HTTPException(status_code=404, detail="用户不存在")
    return {"id": user.id, "username": user.username, "email": user.email, "full_name": user.full_name,
            "role": user.role, "is_active": user.is_active, "created_at": str(user.created_at) if user.created_at else None}


# ---- 更新用户 ----
@router.put("/users/{user_id}")
async def update_user(user_id: int, password: Optional[str] = Query(None), email: Optional[str] = Query(None),
                       full_name: Optional[str] = Query(None), is_active: Optional[bool] = Query(None),
                       role: Optional[int] = Query(None),
                       current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db)):
    user_query = await db.execute(select(User).where(User.id == user_id))
    user = user_query.scalar()
    if not user: raise HTTPException(status_code=404, detail="用户不存在")
    if password: user.password = get_password_hash(password)
    if email: user.email = email
    if full_name: user.full_name = full_name
    if is_active is not None: user.is_active = is_active
    if role is not None: user.role = role
    await db.commit(); await db.refresh(user)
    return {"id": user.id, "username": user.username, "message": "更新成功"}


# ---- 删除用户 ----
@router.delete("/users/{user_id}")
async def delete_user(user_id: int, current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db)):
    user_query = await db.execute(select(User).where(User.id == user_id))
    user = user_query.scalar()
    if not user: raise HTTPException(status_code=404, detail="用户不存在")
    await db.delete(user); await db.commit()
    return {"message": "用户已删除"}
