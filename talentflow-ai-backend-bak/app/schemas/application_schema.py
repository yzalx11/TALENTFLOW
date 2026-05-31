# app/schemas/application_schema.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ApplicationReview(BaseModel):
    action: str = Field(..., pattern="^(pass|reject)$", description="审核动作: pass=通过, reject=驳回")
    review_comment: Optional[str] = Field(default=None, description="审核评语")


class ApplicationOut(BaseModel):
    id: int
    user_id: int
    job_id: Optional[int] = None
    task_id: Optional[int] = None
    resume_id: Optional[int] = None
    cover_letter: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
