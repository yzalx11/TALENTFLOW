# app/models/job.py
import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from app.models.base import Base

class JobPosition(Base):
    """
    职位实体模型 (严格映射到底层 MySQL 的 job_positions 表)
    """
    __tablename__ = "job_positions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_id = Column(String(50), unique=True, nullable=True, index=True, comment="业务职位ID")
    title = Column(String(150), nullable=False, index=True, comment="职位名称")
    company = Column(String(100), nullable=False, comment="公司名称")
    
    salary = Column(String(50), nullable=True, comment="薪资范围")
    required_skills = Column(JSON, nullable=True, comment="职位要求技能列表")
    description = Column(Text, nullable=True, comment="职位描述全文(用于向量化)")
    
    location = Column(String(100), nullable=True, comment="工作地点")
    experience_requirement = Column(String(100), nullable=True, comment="经验要求")
    education_requirement = Column(String(100), nullable=True, comment="学历要求")
    
    # MySQL的 tinyint(1) 在 SQLAlchemy 中通常映射为 Boolean
    is_active = Column(Boolean, default=True, comment="是否有效")
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, comment="更新时间")