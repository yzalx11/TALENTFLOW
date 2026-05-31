# app/api/v1/mentor/task_manager.py
"""
导师端任务管理 — 发布/列表/更新/删除，所有操作限定 mentor_id
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.models.task import Task
from app.models.user import User
from app.schemas import task_schema
from app.core.database import get_db
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/v1/mentor", tags=["Mentor-Tasks"])


def _require_mentor(current_user: User) -> User:
    if current_user.role != 2:
        raise HTTPException(status_code=403, detail="仅导师可访问")
    return current_user


@router.post("/tasks", response_model=task_schema.TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: task_schema.TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mentor = _require_mentor(current_user)
    new_task = Task(**task_in.model_dump(), mentor_id=mentor.id)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@router.get("/tasks")
def list_tasks(
    skip: int = 0,
    limit: int = 50,
    keyword: Optional[str] = Query(None),
    task_status: Optional[int] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.application import Application
    mentor = _require_mentor(current_user)
    query = db.query(Task).filter(Task.mentor_id == mentor.id)
    if keyword:
        from sqlalchemy import or_
        query = query.filter(or_(
            Task.title.like(f"%{keyword}%"),
            Task.description.like(f"%{keyword}%"),
        ))
    if task_status is not None:
        query = query.filter(Task.status == task_status)
    tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()

    # 带出接单人信息
    taken_ids = [t.taken_by for t in tasks if t.taken_by]
    users_map = {}
    apps_map = {}
    if taken_ids:
        for u in db.query(User).filter(User.id.in_(taken_ids)).all():
            users_map[u.id] = u.full_name or u.username
        apps = db.query(Application).filter(
            Application.task_id.in_([t.id for t in tasks]),
            Application.status == "approved"
        ).all()
        for a in apps:
            apps_map[a.task_id] = str(a.updated_at or a.created_at)[:16] if a.updated_at or a.created_at else None

    return [
        {
            "id": t.id, "title": t.title, "description": t.description,
            "category": t.category, "price": t.price, "duration": t.duration,
            "difficulty": t.difficulty, "skills": t.skills or [],
            "status": t.status,
            "taken_by": t.taken_by,
            "taken_by_name": users_map.get(t.taken_by, ""),
            "taken_at": apps_map.get(t.id, ""),
            "created_at": str(t.created_at) if hasattr(t, 'created_at') and t.created_at else None,
        }
        for t in tasks
    ]


@router.put("/tasks/{task_id}", response_model=task_schema.TaskOut)
def update_task(
    task_id: int,
    task_in: task_schema.TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mentor = _require_mentor(current_user)
    task = db.query(Task).filter(Task.id == task_id, Task.mentor_id == mentor.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或无权操作")
    if task.status == 3:
        raise HTTPException(status_code=400, detail="任务已被接取，不可修改")

    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mentor = _require_mentor(current_user)
    task = db.query(Task).filter(Task.id == task_id, Task.mentor_id == mentor.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或无权操作")
    if task.status == 3:
        raise HTTPException(status_code=400, detail="任务已被接取，不可删除")
    db.delete(task)
    db.commit()
    return {"message": f"任务 ID {task_id} 已删除"}
