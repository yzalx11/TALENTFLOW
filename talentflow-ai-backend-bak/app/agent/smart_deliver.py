# app/agent/smart_deliver.py
"""
单岗位智能投递 — 用户对一个岗位点"投递简历"时的智能处理
针对单个 job 的精准投递
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.models.user import User
from app.core.deps import get_current_user
from app.core.logger import logger

router = APIRouter(prefix="/api/v1/user", tags=["SmartDeliver"])


class SmartDeliverRequest(BaseModel):
    job_id: int = Field(..., description="目标岗位 ID")
    mode: str = Field(default="auto", pattern="^(auto|force_generate|force_reuse)$")


class SmartDeliverResponse(BaseModel):
    success: bool
    message: str = ""
    cover_letter: str = ""
    is_reused: bool = False


@router.post("/smart-deliver")
async def smart_deliver(
    data: SmartDeliverRequest,
    current_user: User = Depends(get_current_user),
):
    """
    单岗位智能投递 — 查缓存 → 投递 → 返回求职信
    """
    from app.core.database import SessionLocal
    from app.models.application import Application
    from app.models.resume import Resume

    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(
            Resume.user_id == current_user.id, Resume.is_default == 1
        ).first()
        if not resume:
            resume = db.query(Resume).filter(
                Resume.user_id == current_user.id
            ).order_by(Resume.id.desc()).first()
        if not resume:
            return SmartDeliverResponse(success=False, message="请先创建简历")

        # 查缓存：是否有已优化的简历
        is_reused = False
        if data.mode != "force_generate":
            existing = db.query(Application).filter(
                Application.user_id == current_user.id,
                Application.job_id == data.job_id,
            ).first()
            if existing:
                is_reused = True
                return SmartDeliverResponse(
                    success=True,
                    message="您已投递过该岗位",
                    cover_letter="",
                    is_reused=True,
                )

        # 创建投递（带简历）
        app = Application(
            user_id=current_user.id, job_id=data.job_id, resume_id=resume.id, status="applied"
        )
        db.add(app)
        db.commit()

        logger.info(f"[SmartDeliver] user={current_user.id} job={data.job_id} reused={is_reused}")
        return SmartDeliverResponse(
            success=True,
            message="投递成功",
            cover_letter="",
            is_reused=is_reused,
        )
    except Exception as e:
        db.rollback()
        return SmartDeliverResponse(success=False, message=str(e))
    finally:
        db.close()
