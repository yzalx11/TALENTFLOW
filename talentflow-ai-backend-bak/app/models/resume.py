# app/models/resume.py
import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base


class Resume(Base):
    """
    简历主表 — 合并旧表展示字段 + PPT 处理管道字段
    """
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True, comment="所属用户ID")

    # --- 旧表字段（前端直接使用）---
    name = Column(String(50), nullable=False, index=True, comment="候选人姓名")
    phone = Column(String(30), nullable=True, comment="联系电话")
    email = Column(String(100), nullable=True, comment="电子邮箱")
    title = Column(String(100), nullable=True, comment="意向职位")
    education = Column(String(50), nullable=True, comment="学历")
    experience = Column(String(50), nullable=True, comment="工作经验年限")
    skills = Column(JSON, nullable=True, comment="技能标签(JSON数组，兼容旧前端)")
    summary = Column(Text, nullable=True, comment="个人简介")
    project_experience = Column(Text, nullable=True, comment="项目经验")
    work_experience = Column(Text, nullable=True, comment="工作经历详情")
    source = Column(String(50), nullable=True, comment="简历来源")
    is_default = Column(Integer, default=0, comment="是否默认简历: 0否 1是")

    # --- PPT 处理管道新增字段 ---
    raw_text = Column(Text, nullable=True, comment="原始解析全文，用于审核回溯")
    file_path = Column(String(255), nullable=True, comment="上传简历文件路径")

    status = Column(
        String(20), default="pending", index=True,
        comment="状态: pending=待处理, processed=已提取待审核, reviewed=已审核"
    )

    created_at = Column(DateTime, default=datetime.datetime.utcnow, comment="创建时间")
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow, comment="最后更新时间"
    )

    # 关联到 resume_skills 表（标准化技能）
    resume_skills = relationship("ResumeSkill", back_populates="resume", cascade="all, delete-orphan")
