# app/agent/smart_deliver.py
"""单岗位智能投递 — 查简历 + 生成求职信 + 创建投递记录"""
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
    job_id: int = Field(...)
    mode: str = Field(default="auto", pattern="^(auto|force_generate|force_reuse)$")


def _generate_cover_letter(resume: Resume, job_title: str, job_desc: str) -> str:
    """调用 LLM 为单个岗位生成求职信"""
    try:
        from app.core.llm import get_llm
        from app.agent.skills import load_skill

        llm = get_llm()
        if not llm:
            return ""

        skills = ", ".join(resume.skills or [])
        education = resume.education or ""
        experience = resume.work_experience or resume.summary or ""
        prompt = f"""{load_skill("generate_letter")}

目标岗位: {job_title}: {job_desc[:200]}

候选人背景:
- 学历: {education}
- 技能: {skills}
- 经历: {experience}

请只生成一条求职信文本（纯文本，不要JSON），80-120字。"""
        response = llm.invoke(prompt)
        return response.content.strip().strip('"')
    except Exception as e:
        logger.warning(f"[SmartDeliver] cover letter generation skipped: {e}")
        return ""


@router.post("/smart-deliver")
async def smart_deliver(
    data: SmartDeliverRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """手动投递单个岗位，自动生成求职信"""
    # 查简历
    resume_result = await db.execute(select(Resume).where(
        Resume.user_id == current_user.id, Resume.is_default == 1, Resume.status == "reviewed"
    ))
    resume = resume_result.scalar()
    if not resume:
        resume_result = await db.execute(select(Resume).where(
            Resume.user_id == current_user.id, Resume.status.in_(["processed", "reviewed"])
        ).order_by(Resume.id.desc()).limit(1))
        resume = resume_result.scalar()
    if not resume:
        return {"success": False, "message": "请先创建简历并等待审核"}

    # 防重复
    if data.mode != "force_generate":
        existing = await db.execute(select(Application.id).where(
            Application.user_id == current_user.id, Application.job_id == data.job_id
        ))
        if existing.scalar():
            return {"success": True, "message": "您已投递过该岗位", "is_reused": True}

    # 查岗位信息
    from app.models.job_position import JobPosition
    job_result = await db.execute(select(JobPosition).where(JobPosition.id == data.job_id))
    job = job_result.scalar()
    job_title = job.title if job else ""
    job_desc = job.description if job else ""

    # 生成求职信
    cover_letter = _generate_cover_letter(resume, job_title, job_desc)

    app = Application(
        user_id=current_user.id, job_id=data.job_id,
        resume_id=resume.id, cover_letter=cover_letter, status="applied",
    )
    db.add(app); await db.commit()
    logger.info(f"[SmartDeliver] user={current_user.id} job={data.job_id} letter={len(cover_letter)} chars")
    return {"success": True, "message": "投递成功", "cover_letter": cover_letter}
