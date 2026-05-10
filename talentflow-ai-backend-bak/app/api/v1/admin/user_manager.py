from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from typing import List, Optional
from app.models.user import User
from app.core.database import get_db
from app.core.security import get_password_hash  # 假设你有这个工具函数
from app.core.deps import get_current_active_admin  # 假设你有这个依赖, 用于验证管理员权限

from app.schemas.user_schema import UserRead

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-User-Manager"])

