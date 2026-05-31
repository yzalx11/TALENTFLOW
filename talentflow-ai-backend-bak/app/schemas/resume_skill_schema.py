# app/schemas/resume_skill_schema.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ResumeSkillCreate(BaseModel):
    resume_id: int = Field(..., description="简历ID")
    skill_id: int = Field(..., description="标准技能ID")


class ResumeSkillOut(BaseModel):
    id: int
    resume_id: int
    skill_id: int
    created_at: datetime

    class Config:
        from_attributes = True
