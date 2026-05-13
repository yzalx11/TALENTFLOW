# app/api/v1/admin/job_manager.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from app.models.job_position import JobPosition
from app.models.user import User
from app.schemas import job_schema
from app.core.database import get_db
from app.core.deps import get_current_active_admin

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-Jobs"])

@router.post("/jobs", response_model=job_schema.JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    job_in: job_schema.JobCreate,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    管理员发布新职位
    字段匹配：job_id, title, company, salary, required_skills, description, is_active
    """
    # 检查 job_id 是否已存在
    existing_job = db.query(JobPosition).filter(JobPosition.job_id == job_in.job_id).first()
    if existing_job:
        raise HTTPException(status_code=400, detail="该业务职位ID已存在")

    new_job = JobPosition(**job_in.model_dump())
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@router.get("/jobs", response_model=List[job_schema.JobOut])
def read_jobs(
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = Query(None, description="搜索职位名称、公司或业务ID"),
    is_active: Optional[bool] = Query(None, description="过滤是否有效职位"),
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    管理员获取职位列表 (支持分页和多字段模糊搜索)
    """
    query = db.query(JobPosition)
    
    # 模糊搜索逻辑：匹配标题、公司名称或业务ID
    if keyword:
        query = query.filter(
            or_(
                JobPosition.title.like(f"%{keyword}%"),
                JobPosition.company.like(f"%{keyword}%"),
                JobPosition.job_id.like(f"%{keyword}%")
            )
        )
    
    # 状态过滤
    if is_active is not None:
        query = query.filter(JobPosition.is_active == is_active)

    return query.offset(skip).limit(limit).all()

@router.put("/jobs/{id}", response_model=job_schema.JobOut)
def update_job(
    id: int,
    job_in: job_schema.JobUpdate,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    管理员更新职位信息
    使用数据库自增 ID 进行定位
    """
    job = db.query(JobPosition).filter(JobPosition.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="该职位记录不存在")
        
    update_data = job_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)
        
    db.commit()
    db.refresh(job)
    return job

@router.delete("/jobs/{id}")
def delete_job(
    id: int,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    管理员删除职位记录
    """
    job = db.query(JobPosition).filter(JobPosition.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="该职位记录不存在")
        
    db.delete(job)
    db.commit()
    return {"message": f"职位 (ID: {id}, JobID: {job.job_id}) 已成功删除"}