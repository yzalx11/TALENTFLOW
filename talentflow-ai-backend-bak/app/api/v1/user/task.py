# app/api/v1/user/task.py
"""用户端 — 任务广场 + 岗位浏览 + 投递记录"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.models.task import Task
from app.models.application import Application
from app.models.user import User
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.logger import logger

router = APIRouter(prefix="/api/v1/user", tags=["User-Tasks"])


async def _get_default_resume_id(user_id: int, db: AsyncSession) -> int | None:
    from app.models.resume import Resume
    for statuses in [["reviewed"], ["processed", "reviewed"]]:
        query = await db.execute(select(Resume.id).where(
            Resume.user_id == user_id, Resume.is_default == 1, Resume.status.in_(statuses)
        ))
        resume_id = query.scalar()
        if resume_id:
            return resume_id
    query = await db.execute(select(Resume.id).where(
        Resume.user_id == user_id, Resume.status.in_(["processed", "reviewed"])
    ).order_by(Resume.id.desc()).limit(1))
    return query.scalar()


@router.get("/tasks")
async def list_tasks(
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=20),
    keyword: str = Query(""), category: str = Query(""), difficulty: str = Query(""),
    sort_by: str = Query("created_at", pattern="^(created_at|price)$"),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    conditions = [Task.status.in_([1, 2])]
    if keyword: conditions.append(or_(Task.title.like(f"%{keyword}%"), Task.description.like(f"%{keyword}%")))
    if category: conditions.append(Task.category == category)
    if difficulty: conditions.append(Task.difficulty == difficulty)

    count_query = await db.execute(select(func.count(Task.id)).where(*conditions))
    total = count_query.scalar()

    order = Task.price.desc() if sort_by == "price" else Task.created_at.desc()
    task_query = await db.execute(select(Task).where(*conditions).order_by(order).offset(skip).limit(limit))
    tasks = task_query.scalars().all()

    enrolled_ids = set()
    if tasks:
        task_ids = [t.id for t in tasks]
        app_query = await db.execute(select(Application.task_id).where(
            Application.user_id == current_user.id, Application.task_id.in_(task_ids)
        ))
        enrolled_ids = {row[0] for row in app_query.fetchall()}

    mentor_ids = list({t.mentor_id for t in tasks if t.mentor_id})
    mentors = {}
    if mentor_ids:
        mentor_query = await db.execute(select(User.id, User.full_name, User.username).where(User.id.in_(mentor_ids)))
        for row in mentor_query.fetchall():
            mentors[row[0]] = row[1] or row[2]

    return {
        "items": [{
            "id": t.id, "title": t.title, "description": (t.description or "")[:150],
            "category": t.category, "price": t.price, "duration": t.duration,
            "difficulty": t.difficulty, "skills": t.skills or [], "status": t.status,
            "is_enrolled": t.id in enrolled_ids,
            "mentor_name": mentors.get(t.mentor_id, "未知"),
            "created_at": str(t.created_at) if t.created_at else None,
        } for t in tasks],
        "total": total,
    }


@router.get("/tasks/{task_id}")
async def get_task_detail(task_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task_query = await db.execute(select(Task).where(Task.id == task_id))
    task = task_query.scalar()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    mentor_name = ""
    if task.mentor_id:
        mentor_query = await db.execute(select(User.full_name, User.username).where(User.id == task.mentor_id))
        row = mentor_query.first()
        if row:
            mentor_name = row[0] or row[1]
    return {
        "id": task.id, "title": task.title, "description": task.description,
        "category": task.category, "price": task.price, "duration": task.duration,
        "difficulty": task.difficulty, "skills": task.skills or [], "status": task.status,
        "mentor_name": mentor_name,
        "created_at": str(task.created_at) if task.created_at else None,
    }


@router.post("/tasks/{task_id}/apply")
async def apply_task(task_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task_query = await db.execute(select(Task).where(Task.id == task_id))
    task = task_query.scalar()
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    if task.status != 1: raise HTTPException(status_code=400, detail="任务不可接单")

    existing = await db.execute(select(Application.id).where(
        Application.user_id == current_user.id, Application.task_id == task_id
    ))
    if existing.scalar(): raise HTTPException(status_code=400, detail="您已投递过该任务")

    app = Application(
        user_id=current_user.id, task_id=task_id,
        resume_id=await _get_default_resume_id(current_user.id, db), status="applied",
    )
    db.add(app); await db.commit()
    logger.info(f"📨 学生 {current_user.id} 投递任务 {task_id}")
    return {"message": "投递成功", "application_id": app.id}


@router.post("/jobs/{job_id}/apply")
async def apply_job(job_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Application.id).where(
        Application.user_id == current_user.id, Application.job_id == job_id
    ))
    if existing.scalar(): raise HTTPException(status_code=400, detail="您已投递过该岗位")

    app = Application(
        user_id=current_user.id, job_id=job_id,
        resume_id=await _get_default_resume_id(current_user.id, db), status="applied",
    )
    db.add(app); await db.commit()
    logger.info(f"📨 用户 {current_user.id} 投递岗位 {job_id}")
    return {"message": "投递成功", "application_id": app.id}


@router.get("/jobs")
async def list_jobs(
    skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50),
    keyword: str = Query(""),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    from app.models.job_position import JobPosition
    conditions = [JobPosition.is_active == True]
    if keyword: conditions.append(or_(JobPosition.title.like(f"%{keyword}%"), JobPosition.company.like(f"%{keyword}%")))

    count_query = await db.execute(select(func.count(JobPosition.id)).where(*conditions))
    total = count_query.scalar()

    job_query = await db.execute(select(JobPosition).where(*conditions).order_by(JobPosition.created_at.desc()).offset(skip).limit(limit))
    jobs = job_query.scalars().all()

    applied_ids = set()
    if jobs:
        job_ids = [j.id for j in jobs]
        app_query = await db.execute(select(Application.job_id).where(
            Application.user_id == current_user.id, Application.job_id.in_(job_ids)
        ))
        applied_ids = {row[0] for row in app_query.fetchall()}

    return {
        "items": [{
            "id": j.id, "title": j.title, "company": j.company,
            "salary": j.salary, "location": j.location,
            "experience_requirement": j.experience_requirement,
            "education_requirement": j.education_requirement,
            "required_skills": j.required_skills or [],
            "description": (j.description or "")[:150],
            "is_applied": j.id in applied_ids,
        } for j in jobs],
        "total": total,
    }


@router.get("/applications")
async def list_my_applications(
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    from app.models.job_position import JobPosition
    from app.models.resume import Resume

    count_query = await db.execute(select(func.count(Application.id)).where(Application.user_id == current_user.id))
    total = count_query.scalar()

    app_query = await db.execute(select(Application).where(
        Application.user_id == current_user.id
    ).order_by(Application.created_at.desc()).offset(skip).limit(limit))
    apps = app_query.scalars().all()

    # --- 关联查询：岗位、任务、简历 ---
    job_ids = [str(a.job_id) for a in apps if a.job_id]
    task_ids = [int(a.task_id) for a in apps if a.task_id]
    job_map, task_map, resume_map = {}, {}, {}

    if job_ids:
        numeric_ids = [int(j) for j in job_ids if j.isdigit()]
        string_ids = [j for j in job_ids if not j.isdigit()]
        if numeric_ids:
            job_row_query = await db.execute(select(JobPosition.id, JobPosition.title, JobPosition.company).where(JobPosition.id.in_(numeric_ids)))
            for row in job_row_query.fetchall():
                job_map[str(row[0])] = {"title": row[1], "company": row[2] or ""}
        if string_ids:
            job_row_query2 = await db.execute(select(JobPosition.job_id, JobPosition.title, JobPosition.company).where(JobPosition.job_id.in_(string_ids)))
            for row in job_row_query2.fetchall():
                job_map[row[0]] = {"title": row[1], "company": row[2] or ""}

    if task_ids:
        task_query = await db.execute(select(Task.id, Task.title).where(Task.id.in_(task_ids)))
        for row in task_query.fetchall():
            task_map[str(row[0])] = {"title": row[1], "company": ""}

    resume_ids = [a.resume_id for a in apps if a.resume_id]
    if resume_ids:
        resume_query = await db.execute(select(Resume.id, Resume.title, Resume.name).where(Resume.id.in_(resume_ids)))
        for row in resume_query.fetchall():
            resume_map[row[0]] = row[1] or row[2]

    return {
        "items": [{
            "id": a.id, "job_id": a.job_id, "task_id": a.task_id,
            "target_title": (job_map.get(str(a.job_id)) or task_map.get(str(a.task_id)) or {}).get("title", "未知"),
            "company": (job_map.get(str(a.job_id)) or {}).get("company", ""),
            "resume_title": resume_map.get(a.resume_id, ""),
            "target_type": "智能投递" if (a.job_id and a.cover_letter) else ("任务接单" if a.task_id else "手动投递"),
            "status": a.status,
            "created_at": str(a.created_at) if a.created_at else None,
        } for a in apps],
        "total": total,
    }
