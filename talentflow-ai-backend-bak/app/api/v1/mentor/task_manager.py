# app/api/v1/mentor/task_manager.py
"""导师端任务管理 — 发布/列表/编辑/删除，mentor_id 隔离"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import Optional
from app.models.task import Task
from app.models.user import User
from app.schemas import task_schema
from app.core.database import get_db
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/v1/mentor", tags=["Mentor-Tasks"])


def _require_mentor(current_user: User) -> User:
    if current_user.role != 2: raise HTTPException(status_code=403, detail="仅导师可访问")
    return current_user


# ---- 发布新任务 ----
@router.post("/tasks", response_model=task_schema.TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(task_in: task_schema.TaskCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    mentor = _require_mentor(current_user)
    task = Task(**task_in.model_dump(), mentor_id=mentor.id)
    db.add(task); await db.commit(); await db.refresh(task)
    return task


# ---- 任务列表（仅自己的） ----
@router.get("/tasks")
async def list_tasks(
    skip: int = 0, limit: int = 50,
    keyword: Optional[str] = Query(None), task_status: Optional[int] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    from app.models.application import Application
    mentor = _require_mentor(current_user)
    conditions = [Task.mentor_id == mentor.id]
    if keyword: conditions.append(or_(Task.title.like(f"%{keyword}%"), Task.description.like(f"%{keyword}%")))
    if task_status is not None: conditions.append(Task.status == task_status)

    task_query = await db.execute(select(Task).where(*conditions).order_by(Task.created_at.desc()).offset(skip).limit(limit))
    tasks = task_query.scalars().all()

    # 接单人信息
    taken_ids = [t.taken_by for t in tasks if t.taken_by]
    user_map, approved_map = {}, {}
    if taken_ids:
        user_query = await db.execute(select(User.id, User.full_name, User.username).where(User.id.in_(taken_ids)))
        for row in user_query.fetchall(): user_map[row[0]] = row[1] or row[2]

        approved_query = await db.execute(select(Application.task_id, Application.updated_at).where(
            Application.task_id.in_([t.id for t in tasks]), Application.status == "approved"
        ))
        for row in approved_query.fetchall(): approved_map[row[0]] = str(row[1])[:16] if row[1] else None

    return [{
        "id": task.id, "title": task.title, "description": task.description,
        "category": task.category, "price": task.price, "duration": task.duration,
        "difficulty": task.difficulty, "skills": task.skills or [], "status": task.status,
        "taken_by": task.taken_by, "taken_by_name": user_map.get(task.taken_by, ""),
        "taken_at": approved_map.get(task.id, ""),
        "created_at": str(task.created_at) if hasattr(task, 'created_at') and task.created_at else None,
    } for task in tasks]


# ---- 编辑任务（锁定检查） ----
@router.put("/tasks/{task_id}", response_model=task_schema.TaskOut)
async def update_task(task_id: int, task_in: task_schema.TaskUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    mentor = _require_mentor(current_user)
    task_query = await db.execute(select(Task).where(Task.id == task_id, Task.mentor_id == mentor.id))
    task = task_query.scalar()
    if not task: raise HTTPException(status_code=404, detail="任务不存在或无权操作")
    if task.status == 3: raise HTTPException(status_code=400, detail="任务已被接取，不可修改")
    for field, value in task_in.model_dump(exclude_unset=True).items(): setattr(task, field, value)
    await db.commit(); await db.refresh(task)
    return task


# ---- 删除任务（锁定检查） ----
@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    mentor = _require_mentor(current_user)
    task_query = await db.execute(select(Task).where(Task.id == task_id, Task.mentor_id == mentor.id))
    task = task_query.scalar()
    if not task: raise HTTPException(status_code=404, detail="任务不存在或无权操作")
    if task.status == 3: raise HTTPException(status_code=400, detail="任务已被接取，不可删除")
    await db.delete(task); await db.commit()
    return {"message": "已删除"}
