# app/agent/router.py
"""
FastAPI 接入层 — 策略模式: auto(省钱) / force_generate(效果) / force_reuse(极速)
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.models.user import User
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/v1/user", tags=["Agent"])


class ApplyRequest(BaseModel):
    mode: str = Field(default="auto", pattern="^(auto|force_generate|force_reuse)$")
    threshold: int = Field(default=60, ge=0, le=100)


class ApplyResponse(BaseModel):
    success: bool
    applied: list[dict] = []
    message: str = ""
    mode_used: str = ""


@router.post("/agent/apply")
async def agent_apply(
    req: ApplyRequest,
    current_user: User = Depends(get_current_user),
):
    """Agent 智能投递入口"""
    if req.mode == "force_reuse":
        return ApplyResponse(success=True, message="缓存模式暂未实现", mode_used=req.mode)

    from app.agent.smart_apply_agent import SmartApplyAgent
    agent = SmartApplyAgent(user_id=current_user.id, mode=req.mode, threshold=req.threshold)
    result = await agent.run()

    applied = result.get("applied", [])
    error = result.get("error")

    return ApplyResponse(
        success=len(applied) > 0,
        applied=applied,
        message=error or (f"成功投递 {len(applied)} 个岗位" if applied else "无匹配岗位"),
        mode_used=req.mode,
    )


@router.get("/agent/status")
def agent_status(current_user: User = Depends(get_current_user)):
    """查询当前用户的投递 Agent 状态"""
    from app.core.database import SessionLocal
    from app.models.application import Application
    db = SessionLocal()
    try:
        apps = db.query(Application).filter(
            Application.user_id == current_user.id
        ).order_by(Application.created_at.desc()).limit(20).all()
        return {
            "total": len(apps),
            "recent": [
                {"job_id": a.job_id, "task_id": a.task_id, "status": a.status,
                 "created_at": str(a.created_at)}
                for a in apps
            ]
        }
    finally:
        db.close()
