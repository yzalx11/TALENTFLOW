# app/api/v1/mentor/delivery_manager.py
"""
导师端审核 — 审核通过/驳回，数据隔离：只能审自己任务的投递
"""
import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.application import Application
from app.models.user import User
from app.schemas.application_schema import ApplicationReview
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.logger import logger

router = APIRouter(prefix="/api/v1/mentor", tags=["Mentor-Reviews"])


def _require_mentor(current_user: User) -> User:
    if current_user.role != 2:
        raise HTTPException(status_code=403, detail="仅导师可访问")
    return current_user


@router.get("/applications")
def list_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出所有投递（任务投递 + 岗位投递）"""
    from app.models.job_position import JobPosition

    mentor = _require_mentor(current_user)

    # 任务投递
    task_rows = (
        db.query(
            Application.id, Application.task_id, Application.job_id,
            Application.user_id, Application.resume_id, Application.cover_letter,
            Application.status, Application.created_at, Application.updated_at,
            Task.title.label("target_title"),
            Task.category, Task.price, Task.difficulty,
            User.full_name.label("user_name"), User.username,
        )
        .join(Task, Task.id == Application.task_id)
        .join(User, User.id == Application.user_id)
        .filter(Task.mentor_id == mentor.id)
        .all()
    )

    # 岗位投递
    job_rows = (
        db.query(
            Application.id, Application.task_id, Application.job_id,
            Application.user_id, Application.resume_id, Application.cover_letter,
            Application.status, Application.created_at, Application.updated_at,
            JobPosition.title.label("target_title"),
            JobPosition.company,
            User.full_name.label("user_name"), User.username,
        )
        .outerjoin(JobPosition, JobPosition.id == Application.job_id)
        .join(User, User.id == Application.user_id)
        .all()
    )

    all_rows = sorted(
        list(task_rows) + list(job_rows),
        key=lambda r: r.created_at, reverse=True
    )

    return [
        {
            "id": r.id,
            "task_id": r.task_id,
            "job_id": r.job_id,
            "target_title": r.target_title,
            "target_type": "任务" if r.task_id else "岗位",
            "category": getattr(r, "category", "") or "",
            "price": getattr(r, "price", 0) or 0,
            "difficulty": getattr(r, "difficulty", "") or "",
            "company": getattr(r, "company", "") or "",
            "user_id": r.user_id,
            "user_name": r.user_name or r.username,
            "resume_id": r.resume_id,
            "cover_letter": r.cover_letter,
            "status": r.status,
            "created_at": str(r.created_at) if r.created_at else None,
            "updated_at": str(r.updated_at) if r.updated_at else None,
        }
        for r in all_rows[:50]
    ]


@router.post("/applications/{application_id}/review")
def review_application(
    application_id: int,
    data: ApplicationReview,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    审核投递。防横向越权：校验投递所属任务是否为当前导师发布。
    """
    mentor = _require_mentor(current_user)

    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="投递记录不存在")

    if app.task_id:
        # 任务投递 — 校验归属
        task = db.query(Task).filter(
            Task.id == app.task_id, Task.mentor_id == mentor.id,
        ).first()
        if not task:
            raise HTTPException(status_code=403, detail="无权审核此投递")
        if data.action == "pass":
            task.taken_by = app.user_id
            task.status = 3
        else:
            task.taken_by = None
            task.status = 1

    if app.status != "applied":
        raise HTTPException(status_code=400, detail="该投递已被审核，不可重复操作")

    new_status = "approved" if data.action == "pass" else "rejected"
    app.status = new_status
    app.updated_at = datetime.datetime.utcnow()

    db.commit()
    logger.info(f"✅ 导师 {mentor.id} 审核投递 {application_id}: {new_status}")
    return {
        "application_id": application_id,
        "status": new_status,
        "message": "审核通过" if new_status == "approved" else "已驳回，任务重新开放",
    }


@router.get("/resumes/{resume_id}")
def get_resume_detail(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导师查看简历详情"""
    _ = _require_mentor(current_user)
    from app.models.resume import Resume
    r = db.query(Resume).filter(Resume.id == resume_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    return {
        "id": r.id, "name": r.name, "title": r.title, "phone": r.phone,
        "email": r.email, "education": r.education, "experience": r.experience,
        "skills": r.skills or [], "summary": r.summary,
        "work_experience": r.work_experience, "project_experience": r.project_experience,
    }
