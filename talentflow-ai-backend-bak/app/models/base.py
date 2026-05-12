import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Column, Integer, String, Boolean, DateTime, or_
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

class UserDB(Base):
    """
    用户核心实体模型 (映射到底层 MySQL 的 users 表)
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # 账号信息
    username = Column(String(50), unique=True, nullable=False, index=True, comment="登录账号")
    password = Column(String(255), nullable=False, comment="Argon2加密后的密码")
    email = Column(String(100), unique=True, index=True, nullable=True, comment="电子邮箱")
    # 业务信息
    full_name = Column(String(50), nullable=True, comment="真实姓名")
    is_active = Column(Boolean, default=True, comment="是否激活: 1正常, 0封禁")
    role = Column(Integer, default=0, nullable=False, comment="角色: 0求职者, 1导师, 2管理员")
    # 审计时间
    created_at = Column(DateTime, default=datetime.datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, comment="最后更新时间")
