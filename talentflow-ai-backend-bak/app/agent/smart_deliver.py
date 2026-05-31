# app/agent/smart_deliver.py
"""单岗位智能投递"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.application import Application
from app.models.resume import Resume
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.logger import logger

router = APIRouter(prefix="/api/v1/user", tags=["SmartDeliver"])


class SmartDeliverRequest(BaseModel):
    job_id: int = Field(...); mode: str = Field(default="auto", pattern="^(auto|force_generate|force_reuse)$")


@router.post("/smart-deliver")
async def smart_deliver(data: SmartDeliverRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Resume).where(Resume.user_id == current_user.id, Resume.is_default == 1, Resume.status == "reviewed"))
    resume = r.scalar()
    if not resume:
        r2 = await db.execute(select(Resume).where(Resume.user_id == current_user.id, Resume.status.in_(["processed", "reviewed"])).order_by(Resume.id.desc()).limit(1))
        resume = r2.scalar()
    if not resume: return {"success": False, "message": "请先创建简历并等待审核"}

    if data.mode != "force_generate":
        ex = await db.execute(select(Application.id).where(Application.user_id == current_user.id, Application.job_id == data.job_id))
        if ex.scalar(): return {"success": True, "message": "您已投递过该岗位", "is_reused": True}

    app = Application(user_id=current_user.id, job_id=data.job_id, resume_id=resume.id, status="applied")
    db.add(app); await db.commit()
    logger.info(f"[SmartDeliver] user={current_user.id} job={data.job_id}")
    return {"success": True, "message": "投递成功"}
