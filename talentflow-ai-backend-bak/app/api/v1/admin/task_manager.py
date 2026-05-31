# app/api/v1/admin/task_manager.py
"""管理员端 — 任务管理"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional

from app.models.task import Task
from app.schemas import task_schema
from app.models.user import User
from app.core.database import get_db
from app.core.deps import get_current_active_admin

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-Tasks"])


# ---- 创建任务 ----
@router.post("/tasks", response_model=task_schema.TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(task_in: task_schema.TaskCreate, current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db)):
    task = Task(**task_in.model_dump())
    db.add(task); await db.commit(); await db.refresh(task)
    return task


# ---- 任务列表 ----
@router.get("/tasks", response_model=List[task_schema.TaskOut])
async def read_tasks(
    skip: int = 0, limit: int = 100,
    keyword: Optional[str] = Query(None), task_status: Optional[int] = Query(None, alias="status"),
    current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db),
):
    conditions = []
    if keyword: conditions.append(or_(Task.title.like(f"%{keyword}%"), Task.description.like(f"%{keyword}%")))
    if task_status is not None: conditions.append(Task.status == task_status)
    task_query = await db.execute(select(Task).where(*conditions).offset(skip).limit(limit))
    return task_query.scalars().all()


# ---- 更新任务 ----
@router.put("/tasks/{task_id}", response_model=task_schema.TaskOut)
async def update_task(task_id: int, task_in: task_schema.TaskUpdate, current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db)):
    task_query = await db.execute(select(Task).where(Task.id == task_id))
    task = task_query.scalar()
    if not task: raise HTTPException(status_code=404, detail="该任务不存在")
    for field, value in task_in.model_dump(exclude_unset=True).items(): setattr(task, field, value)
    await db.commit(); await db.refresh(task)
    return task


# ---- 删除任务 ----
@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db)):
    task_query = await db.execute(select(Task).where(Task.id == task_id))
    task = task_query.scalar()
    if not task: raise HTTPException(status_code=404, detail="该任务不存在")
    await db.delete(task); await db.commit()
    return {"message": f"任务 ID {task_id} 已被成功删除"}
