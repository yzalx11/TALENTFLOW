# app/schemas/skills_schema.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SkillDictBase(BaseModel):
    standard_name: str = Field(..., min_length=1, max_length=100, description="标准技能名称")
    category: Optional[str] = Field(default=None, max_length=50, description="技能分类")


class SkillDictCreate(SkillDictBase):
    pass


class SkillDictUpdate(BaseModel):
    standard_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, max_length=50)


class SkillDictOut(SkillDictBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
