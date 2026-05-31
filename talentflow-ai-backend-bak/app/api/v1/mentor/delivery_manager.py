# app/api/v1/mentor/delivery_manager.py
"""导师端 — 投递列表 + 审核 + 简历查看"""
import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.task import Task
from app.models.application import Application
from app.models.user import User
from app.schemas.application_schema import ApplicationReview
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.logger import logger

router = APIRouter(prefix="/api/v1/mentor", tags=["Mentor-Reviews"])


def _require_mentor(current_user: User) -> User:
    if current_user.role != 2: raise HTTPException(status_code=403, detail="仅导师可访问")
    return current_user


@router.get("/applications")
async def list_applications(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.job_position import JobPosition
    mentor = _require_mentor(current_user)

    # 任务投递：查 Application + 关联的 Task / User 信息
    task_query = await db.execute(
        select(
            Application, Task.title, Task.category, Task.price, Task.difficulty,
            User.full_name, User.username,
        )
        .join(Task, Task.id == Application.task_id)
        .join(User, User.id == Application.user_id)
        .where(Task.mentor_id == mentor.id)
    )
    task_rows = task_query.fetchall()

    # 岗位投递：查 Application + 关联的 JobPosition / User 信息
    job_query = await db.execute(
        select(
            Application, JobPosition.title, JobPosition.company,
            User.full_name, User.username,
        )
        .outerjoin(JobPosition, JobPosition.id == Application.job_id)
        .join(User, User.id == Application.user_id)
    )
    job_rows = job_query.fetchall()

    application_list = []

    # 组装任务投递结果
    for row in task_rows:
        app = row[0]; task_title = row[1]; category = row[2]; price = row[3]
        difficulty = row[4]; full_name = row[5]; username = row[6]
        application_list.append({
            "id": app.id, "task_id": app.task_id, "job_id": app.job_id,
            "target_title": task_title, "target_type": "任务",
            "category": category, "price": price, "difficulty": difficulty,
            "company": "", "user_id": app.user_id,
            "user_name": full_name or username, "resume_id": app.resume_id,
            "cover_letter": app.cover_letter, "status": app.status,
            "created_at": str(app.created_at) if app.created_at else None,
        })

    # 组装岗位投递结果
    for row in job_rows:
        app = row[0]; job_title = row[1]; company = row[2]
        full_name = row[3]; username = row[4]
        application_list.append({
            "id": app.id, "task_id": app.task_id, "job_id": app.job_id,
            "target_title": job_title, "target_type": "岗位",
            "category": "", "price": 0, "difficulty": "",
            "company": company or "", "user_id": app.user_id,
            "user_name": full_name or username, "resume_id": app.resume_id,
            "cover_letter": app.cover_letter, "status": app.status,
            "created_at": str(app.created_at) if app.created_at else None,
        })

    application_list.sort(key=lambda item: item["created_at"] or "", reverse=True)
    return application_list[:50]


@router.post("/applications/{application_id}/review")
async def review_application(application_id: int, data: ApplicationReview,
                              current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    mentor = _require_mentor(current_user)
    app_query = await db.execute(select(Application).where(Application.id == application_id))
    application = app_query.scalar()
    if not application: raise HTTPException(status_code=404, detail="投递记录不存在")

    if application.task_id:
        task_query = await db.execute(select(Task).where(Task.id == application.task_id, Task.mentor_id == mentor.id))
        task = task_query.scalar()
        if not task: raise HTTPException(status_code=403, detail="无权审核此投递")
        if data.action == "pass": task.taken_by = application.user_id; task.status = 3
        else: task.taken_by = None; task.status = 1

    if application.status != "applied": raise HTTPException(status_code=400, detail="该投递已被审核")
    new_status = "approved" if data.action == "pass" else "rejected"
    application.status = new_status; application.updated_at = datetime.datetime.utcnow()
    await db.commit()
    logger.info(f"✅ 导师 {mentor.id} 审核投递 {application_id}: {new_status}")
    return {"application_id": application_id, "status": new_status,
            "message": "审核通过" if new_status == "approved" else "已驳回"}


@router.get("/resumes/{resume_id}")
async def get_resume_detail(resume_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    _ = _require_mentor(current_user)
    from app.models.resume import Resume
    resume_query = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = resume_query.scalar()
    if not resume: raise HTTPException(status_code=404, detail="简历不存在")
    return {"id": resume.id, "name": resume.name, "title": resume.title, "phone": resume.phone,
            "email": resume.email, "education": resume.education, "experience": resume.experience,
            "skills": resume.skills or [], "summary": resume.summary,
            "work_experience": resume.work_experience, "project_experience": resume.project_experience}
