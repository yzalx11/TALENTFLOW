# app/schemas/resume_schema.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ResumeBase(BaseModel):
    """旧表字段"""
    name: str = Field(..., min_length=1, max_length=50, description="候选人姓名")
    phone: Optional[str] = Field(default=None, max_length=30, description="联系电话")
    email: Optional[str] = Field(default=None, max_length=100, description="电子邮箱")
    title: Optional[str] = Field(default=None, max_length=100, description="意向职位")
    education: Optional[str] = Field(default=None, max_length=50, description="学历")
    experience: Optional[str] = Field(default=None, max_length=50, description="工作经验年限")
    skills: Optional[List[str]] = Field(default=None, description="技能标签(JSON数组)")
    summary: Optional[str] = Field(default=None, description="个人简介")
    project_experience: Optional[str] = Field(default=None, description="项目经验")
    work_experience: Optional[str] = Field(default=None, description="工作经历详情")
    source: Optional[str] = Field(default=None, max_length=50, description="简历来源")


class ResumeCreate(ResumeBase):
    raw_text: Optional[str] = Field(default=None, description="简历原始解析文本")
    file_path: Optional[str] = Field(default=None, description="上传文件路径")


class ResumeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[str] = Field(default=None, max_length=100)
    title: Optional[str] = Field(default=None, max_length=100)
    education: Optional[str] = Field(default=None, max_length=50)
    experience: Optional[str] = Field(default=None, max_length=50)
    skills: Optional[List[str]] = None
    summary: Optional[str] = None
    project_experience: Optional[str] = None
    work_experience: Optional[str] = None
    source: Optional[str] = None


class ResumeOut(ResumeBase):
    id: int
    raw_text: Optional[str] = None
    file_path: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResumeDetailOut(ResumeOut):
    """审核页面聚合：简历 + 关联技能 + 全量标准技能候选"""
    standard_skills: List[dict] = Field(default_factory=list, description="当前关联的标准技能")
    all_skills: List[dict] = Field(default_factory=list, description="全量标准技能词典")


class ResumeReviewSubmit(BaseModel):
    """审核提交"""
    skill_ids: List[int] = Field(default_factory=list, description="审核确认后的标准技能ID列表")
    action: str = Field(default="pass", pattern="^(pass|reject)$", description="pass=通过, reject=驳回")
    review_comment: Optional[str] = Field(default=None, description="审核评语")
