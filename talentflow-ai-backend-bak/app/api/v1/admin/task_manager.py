# app/api/v1/admin/task_manager.py
from fastapi import APIRouter, Depends, HTTPException, Query, status

from sqlalchemy.orm import Session
from sqlalchemy import or_

from typing import List, Optional

# 导入模型和 Schema
from app.models.task import Task
from app.schemas import task_schema
from app.models.user import User
from app.core.database import get_db
from app.core.deps import get_current_active_admin

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-Tasks"])

@router.post("/tasks", response_model=task_schema.TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: task_schema.TaskCreate,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    管理员接口：发布新任务
    """
    # 将前端传来的 schema 数据转换为字典，并存入数据库
    new_task = Task(**task_in.model_dump())
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@router.get("/tasks", response_model=List[task_schema.TaskOut])
def read_tasks(
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = Query(None, description="搜索任务标题或描述"),
    task_status: Optional[int] = Query(None, alias="status", description="按状态过滤: 0待审, 1进行, 2暂停, 3完成"),
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    管理员接口：获取任务列表（支持分页、关键字模糊搜索和状态过滤）
    """
    query = db.query(Task)

    if keyword:
        query = query.filter(
            or_(
                Task.title.like(f"%{keyword}%"),
                Task.description.like(f"%{keyword}%")
            )
        )
    if task_status is not None:
        query = query.filter(Task.status == task_status)

    tasks = query.offset(skip).limit(limit).all()
    return tasks

@router.put("/tasks/{task_id}", response_model=task_schema.TaskOut)
def update_task(
    task_id: int,
    task_in: task_schema.TaskUpdate,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    管理员接口：更新任务信息
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="该任务不存在")
        
    # 动态更新提供的字段 
    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
        
    db.commit()
    db.refresh(task)
    return task

@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    管理员接口：删除指定任务
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="该任务不存在")
        
    db.delete(task)
    db.commit()
    return {"message": f"任务 ID {task_id} 已被成功删除"}