from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# 共享属性
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    role: int = 0  # 0: 求职者, 1: 导师, 2: 管理员

# 注册时使用的 Schema
class UserCreate(UserBase):
    password: str

# 更新时使用的 Schema
class UserUpdate(BaseModel):
    password: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[int] = None

# API 返回给前端的 Schema (不包含密码)
class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# 登录成功后的响应
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut