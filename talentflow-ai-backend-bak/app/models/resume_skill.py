# app/models/resume_skill.py
import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base


class ResumeSkill(Base):
    """
    简历-技能关联表 — 多对多映射，外键约束杜绝脏数据
    """
    __tablename__ = "resume_skills"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True, comment="简历ID")
    skill_id = Column(Integer, ForeignKey("skills_dict.id", ondelete="RESTRICT"), nullable=False, index=True, comment="标准技能ID")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, comment="关联时间")

    # 联合唯一约束：同一简历不重复关联同一技能
    __table_args__ = (
        UniqueConstraint("resume_id", "skill_id", name="uq_resume_skill"),
    )

    # 双向关联
    resume = relationship("Resume", back_populates="resume_skills")
    skill = relationship("SkillDict")
