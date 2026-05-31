# app/models/skills.py
import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.models.base import Base


class SkillDict(Base):
    """
    标准技能词典 — 收录审定后的标准技能名称，消除同义异名
    """
    __tablename__ = "skills_dict"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    standard_name = Column(String(100), unique=True, nullable=False, index=True, comment="标准技能名称")
    category = Column(String(50), nullable=True, index=True, comment="技能分类: 编程语言/框架/工具/数据库/云原生/其他")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, comment="创建时间")
