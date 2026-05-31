import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from app.models.base import Base
class Task(Base):
    """
    任务实体模型 (由 task_schema.py 映射而来)
    """
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(100), nullable=False, index=True, comment="任务标题")
    description = Column(Text, nullable=True, comment="任务详细描述")
    
    category = Column(String(50), nullable=False, comment="分类")
    price = Column(Integer, nullable=False, default=0, comment="金额")
    duration = Column(Integer, nullable=False, comment="工期(天)")
    
    difficulty = Column(String(20), nullable=True, comment="难度")
    skills = Column(JSON, nullable=True, comment="所需技能列表")
    
    # 外键关联
    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True, comment="发布导师ID")
    taken_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="接单学生ID")
    status = Column(Integer, default=0, nullable=False, comment="状态: 0待审核, 1进行中, 2暂停, 3完成")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # owner 关系已移除（未被使用且导致循环引用）