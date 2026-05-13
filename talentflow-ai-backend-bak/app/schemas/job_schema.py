# app/schemas/job_schema.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class JobBase(BaseModel):
    job_id: str = Field(..., description="业务职位ID")
    title: str = Field(..., description="职位名称")
    company: str = Field(..., description="公司名称")
    
    # 新增的三个字段
    location: Optional[str] = Field(default=None, description="工作地点")
    experience_requirement: Optional[str] = Field(default=None, description="经验要求")
    education_requirement: Optional[str] = Field(default=None, description="学历要求")
    
    salary: Optional[str] = Field(default=None, description="薪资范围")
    required_skills: Optional[List[str]] = Field(default=None, description="技能要求")
    description: Optional[str] = Field(default=None, description="职位描述")
    is_active: bool = Field(default=True)

class JobCreate(JobBase):
    pass

class JobUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    experience_requirement: Optional[str] = None
    education_requirement: Optional[str] = None
    salary: Optional[str] = None
    required_skills: Optional[List[str]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class JobOut(JobBase):
    id: int
    pdf_path: Optional[str] = Field(None, description="PDF文件存储路径")
    created_at: datetime
    updated_at: datetime
    

    class Config:
        from_attributes = True