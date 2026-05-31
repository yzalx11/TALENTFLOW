# app/api/v1/user/task.py
"""
用户端任务广场 — 浏览所有导师发布的已发布任务
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from fastapi import HTTPException

from app.models.task import Task
from app.models.application import Application
from app.models.user import User
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.logger import logger

router = APIRouter(prefix="/api/v1/user", tags=["User-Tasks"])


def _get_default_resume_id(user_id: int, db: Session) -> int | None:
    from app.models.resume import Resume
    r = db.query(Resume).filter(Resume.user_id == user_id, Resume.is_default == 1).first()
    if not r:
        r = db.query(Resume).filter(Resume.user_id == user_id).order_by(Resume.id.desc()).first()
    return r.id if r else None


@router.get("/tasks")
def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=20),
    keyword: str = Query("", description="搜索任务标题或描述"),
    category: str = Query("", description="筛选分类"),
    difficulty: str = Query("", description="筛选难度: 简单/中等/困难"),
    sort_by: str = Query("created_at", pattern="^(created_at|price)$", description="排序字段"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """任务广场 — 分页 + 分类筛选 + 排序"""
    query = db.query(Task).filter(Task.status.in_([1, 2]))  # 已发布或已暂停

    if keyword:
        query = query.filter(
            or_(
                Task.title.like(f"%{keyword}%"),
                Task.description.like(f"%{keyword}%"),
            )
        )
    if category:
        query = query.filter(Task.category == category)
    if difficulty:
        query = query.filter(Task.difficulty == difficulty)

    total = query.count()

    if sort_by == "price":
        query = query.order_by(Task.price.desc())
    else:
        query = query.order_by(Task.created_at.desc())

    tasks = query.offset(skip).limit(limit).all()

    # 当前用户已报名的任务 ID 集合
    from app.models.application import Application
    enrolled_ids = set()
    if tasks:
        apps = db.query(Application.task_id).filter(
            Application.user_id == current_user.id,
            Application.task_id.in_([t.id for t in tasks]),
        ).all()
        enrolled_ids = {a[0] for a in apps}

    # 带出导师名
    mentor_ids = list(set(t.mentor_id for t in tasks if t.mentor_id))
    mentors = {}
    if mentor_ids:
        for u in db.query(User).filter(User.id.in_(mentor_ids)).all():
            mentors[u.id] = u.full_name or u.username

    return {
        "items": [
            {
                "id": t.id,
                "title": t.title,
                "description": (t.description or "")[:150],
                "category": t.category,
                "price": t.price,
                "duration": t.duration,
                "difficulty": t.difficulty,
                "skills": t.skills or [],
                "status": t.status,
                "is_enrolled": t.id in enrolled_ids,
                "mentor_name": mentors.get(t.mentor_id, "未知"),
                "created_at": str(t.created_at) if t.created_at else None,
            }
            for t in tasks
        ],
        "total": total,
    }


@router.get("/tasks/{task_id}")
def get_task_detail(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """任务详情"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    mentor_name = ""
    if task.mentor_id:
        m = db.query(User).filter(User.id == task.mentor_id).first()
        if m:
            mentor_name = m.full_name or m.username

    return {
        "id": task.id, "title": task.title, "description": task.description,
        "category": task.category, "price": task.price, "duration": task.duration,
        "difficulty": task.difficulty, "skills": task.skills or [],
        "status": task.status,
        "mentor_name": mentor_name,
        "created_at": str(task.created_at) if task.created_at else None,
    }


@router.post("/tasks/{task_id}/apply")
def apply_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """学生接单 — 创建投递记录，导师端实时可见"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status != 1:
        raise HTTPException(status_code=400, detail="任务不可接单")

    # 防重复投递
    existing = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.task_id == task_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="您已投递过该任务，请等待导师审核")

    app = Application(
        user_id=current_user.id,
        task_id=task_id,
        resume_id=_get_default_resume_id(current_user.id, db),
        status="applied",
    )
    db.add(app)
    db.commit()

    logger.info(f"📨 学生 {current_user.id} 投递任务 {task_id}")
    return {"message": "投递成功，请等待导师审核", "application_id": app.id}


@router.post("/jobs/{job_id}/apply")
def apply_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """单岗位一键投递"""
    existing = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.job_id == job_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="您已投递过该岗位")

    app = Application(user_id=current_user.id, job_id=job_id, resume_id=_get_default_resume_id(current_user.id, db), status="applied")
    db.add(app)
    db.commit()
    logger.info(f"📨 用户 {current_user.id} 投递岗位 {job_id}")
    return {"message": "投递成功", "application_id": app.id}


@router.get("/applications")
def list_my_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我的投递记录"""
    from app.models.job_position import JobPosition
    apps = db.query(Application).filter(
        Application.user_id == current_user.id
    ).order_by(Application.created_at.desc()).limit(50).all()

    job_ids = [str(a.job_id) for a in apps if a.job_id]
    task_ids = [int(a.task_id) for a in apps if a.task_id]
    from app.models.resume import Resume

    jobs = {}; tasks = {}; resumes = {}

    if job_ids:
        ids = [int(j) for j in job_ids if j.isdigit()]
        by_str = [j for j in job_ids if not j.isdigit()]
        if ids:
            for j in db.query(JobPosition).filter(JobPosition.id.in_(ids)).all():
                jobs[str(j.id)] = {"title": j.title, "company": j.company or ""}
        if by_str:
            for j in db.query(JobPosition).filter(JobPosition.job_id.in_(by_str)).all():
                jobs[j.job_id] = {"title": j.title, "company": j.company or ""}
    if task_ids:
        for t in db.query(Task).filter(Task.id.in_(task_ids)).all():
            tasks[str(t.id)] = {"title": t.title, "company": ""}

    # 简历映射
    resume_ids = [a.resume_id for a in apps if a.resume_id]
    if resume_ids:
        for r in db.query(Resume).filter(Resume.id.in_(resume_ids)).all():
            resumes[r.id] = r.title or r.name

    return [
        {
            "id": a.id,
            "job_id": a.job_id,
            "task_id": a.task_id,
            "target_title": (jobs.get(str(a.job_id)) or tasks.get(str(a.task_id)) or {}).get("title", "未知"),
            "company": (jobs.get(str(a.job_id)) or {}).get("company", ""),
            "resume_title": resumes.get(a.resume_id, ""),
            "target_type": "手动投递" if a.job_id and not a.task_id else "任务接单",
            "status": a.status,
            "created_at": str(a.created_at) if a.created_at else None,
        }
        for a in apps
    ]
