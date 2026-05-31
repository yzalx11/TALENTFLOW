# app/models/application.py
import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.models.base import Base


class Application(Base):
    """
    投递/申请记录表 — 映射已有 applications 表
    支持岗位投递(job_id)和任务投递(task_id)
    """
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="申请人ID")
    job_id = Column(Integer, nullable=True, comment="岗位ID（岗位投递时使用）")
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True, comment="任务ID（任务投递时使用）")
    resume_id = Column(Integer, nullable=True, comment="关联简历ID")

    cover_letter = Column(Text, nullable=True, comment="求职信/申请说明")
    status = Column(String(20), default="applied", index=True, comment="状态: applied=已投递, approved=通过, rejected=驳回")

    created_at = Column(DateTime, default=datetime.datetime.utcnow, comment="投递时间")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, comment="审核时间")
