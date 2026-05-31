# app/api/v1/admin/job_manager.py
"""管理员端 — 职位管理（解析/创建/列表/更新/删除/批量导入）"""
from fastapi import APIRouter, Depends, HTTPException, Query, status, Form, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
import json, uuid

from app.models.job_position import JobPosition
from app.models.user import User
from app.schemas import job_schema
from app.core.database import get_db
from app.core.deps import get_current_active_admin
from app.core.logger import logger
from app.core.vector_store import add_documents_to_faiss
from app.core.llm import parse_job_full_info, parse_multiple_jobs_info
from app.utils.file_parser import save_upload_file_to_disk, extract_text_from_local_file, split_text_pure_python
from app.api.v1.admin.skill_manager import standardize_skill_list

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-Jobs"])


# ---- 预解析：上传 JD 文件 → AI 提取字段（不入库） ----
@router.post("/jobs/parse")
async def parse_job_for_form(file: UploadFile = File(...), current_user: User = Depends(get_current_active_admin)):
    file_path = save_upload_file_to_disk(file)
    if not file_path: raise HTTPException(status_code=500, detail="文件上传失败")
    full_text = extract_text_from_local_file(file_path)
    parsed_data = await parse_job_full_info(full_text)
    return {"success": True, "data": parsed_data}


# ---- 创建职位：表单数据 + 文件 → MySQL + FAISS ----
@router.post("/jobs", response_model=job_schema.JobOut, status_code=status.HTTP_201_CREATED)
async def create_job(
    title: str = Form(...), company: str = Form(...),
    salary: Optional[str] = Form(None), location: Optional[str] = Form(None),
    experience_requirement: Optional[str] = Form(None), education_requirement: Optional[str] = Form(None),
    description: Optional[str] = Form(None), required_skills: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db),
):
    # 解析技能
    parsed_skills = []
    if required_skills:
        try:
            parsed_skills = json.loads(required_skills)
            parsed_skills = [s.strip() for s in parsed_skills if isinstance(s, str) and s.strip()]
            parsed_skills = standardize_skill_list(parsed_skills, db)
        except Exception as e: logger.error(f"解析技能失败: {e}")

    job_id = f"JOB-{uuid.uuid4().hex[:8]}"  # 去掉 .upper() 确保小写兼容
    final_description = description or ""

    # 文件处理 + FAISS
    if file:
        try:
            file_path = save_upload_file_to_disk(file)
            if file_path:
                full_text = extract_text_from_local_file(file_path, fallback_text=description or "")
                final_description = final_description or full_text[:1000]
                chunks = [c.strip() for c in split_text_pure_python(full_text, 250, 30) if isinstance(c, str) and c.strip()]
                if chunks:
                    metadatas = [{"job_id": job_id, "source_file": file.filename}] * len(chunks)
                    add_documents_to_faiss(chunks=chunks, metadatas=metadatas)
        except Exception as e: logger.error(f"处理文件失败: {e}")

    new_job = JobPosition(job_id=job_id, title=title.strip(), company=company.strip(),
                          salary=salary.strip() if salary else None, location=location.strip() if location else None,
                          experience_requirement=experience_requirement.strip() if experience_requirement else None,
                          education_requirement=education_requirement.strip() if education_requirement else None,
                          description=final_description.strip() if final_description else None,
                          required_skills=parsed_skills, is_active=True)
    try:
        db.add(new_job); await db.commit(); await db.refresh(new_job)
        return new_job
    except Exception as e:
        await db.rollback(); raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


# ---- 职位列表 ----
@router.get("/jobs", response_model=List[job_schema.JobOut])
async def read_jobs(
    skip: int = 0, limit: int = 100,
    keyword: Optional[str] = Query(None), is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db),
):
    conditions = []
    if keyword: conditions.append(or_(JobPosition.title.like(f"%{keyword}%"), JobPosition.company.like(f"%{keyword}%")))
    if is_active is not None: conditions.append(JobPosition.is_active == is_active)
    job_query = await db.execute(select(JobPosition).where(*conditions).offset(skip).limit(limit))
    return job_query.scalars().all()


# ---- 更新职位 ----
@router.put("/jobs/{id}", response_model=job_schema.JobOut)
async def update_job(
    id: int, title: str = Form(...), company: str = Form(...),
    salary: Optional[str] = Form(None), location: Optional[str] = Form(None),
    experience_requirement: Optional[str] = Form(None), education_requirement: Optional[str] = Form(None),
    required_skills: str = Form("[]"), description: str = Form(""),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db),
):
    job_query = await db.execute(select(JobPosition).where(JobPosition.id == id))
    job = job_query.scalar()
    if not job: raise HTTPException(status_code=404, detail="职位不存在")

    job.title = title; job.company = company; job.salary = salary; job.location = location
    job.experience_requirement = experience_requirement; job.education_requirement = education_requirement
    job.description = description
    try:
        raw_skills = json.loads(required_skills)
        job.required_skills = standardize_skill_list(raw_skills, db)
    except: pass

    if file:
        file_path = save_upload_file_to_disk(file)
        if file_path:
            full_text = extract_text_from_local_file(file_path)
            chunks = split_text_pure_python(full_text)
            if chunks:
                metadatas = [{"job_id": job.job_id, "source_file": file.filename} for _ in chunks]
                add_documents_to_faiss(chunks=chunks, metadatas=metadatas)

    await db.commit(); await db.refresh(job)
    return job


# ---- 删除职位 ----
@router.delete("/jobs/{id}")
async def delete_job(id: int, current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db)):
    job_query = await db.execute(select(JobPosition).where(JobPosition.id == id))
    job = job_query.scalar()
    if not job: raise HTTPException(status_code=404, detail="该职位记录不存在")
    await db.delete(job); await db.commit()
    return {"message": f"职位已删除"}


# ---- 批量导入：上传长文档 → AI 拆分为多个职位 → 全部入库 ----
@router.post("/jobs/batch")
async def batch_import_jobs(file: UploadFile = File(...), current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db)):
    file_path = save_upload_file_to_disk(file)
    if not file_path: raise HTTPException(status_code=500, detail="文件保存失败")

    full_text = extract_text_from_local_file(file_path)
    jobs_data = await parse_multiple_jobs_info(full_text)
    if not jobs_data or not isinstance(jobs_data, list):
        raise HTTPException(status_code=400, detail="AI 未能从文档中提取到职位结构")

    success_count = 0; all_chunks = []; all_metadatas = []
    for job_info in jobs_data:
        job_id = f"JOB-{uuid.uuid4().hex[:8]}"
        new_job = JobPosition(job_id=job_id, title=job_info.get("title") or "未知职位",
                              company=job_info.get("company") or "未知公司", salary=job_info.get("salary") or "面议",
                              location=job_info.get("location") or "不限",
                              experience_requirement=job_info.get("experience_requirement") or "不限",
                              education_requirement=job_info.get("education_requirement") or "不限",
                              description=job_info.get("description") or "",
                              required_skills=job_info.get("required_skills") or [], is_active=True)
        db.add(new_job)
        desc_text = job_info.get("description", "") or f"职位：{new_job.title}，技能：{', '.join(new_job.required_skills)}"
        chunks = split_text_pure_python(desc_text, 250, 30)
        metadatas = [{"job_id": job_id, "company": new_job.company, "source_file": file.filename} for _ in chunks]
        all_chunks.extend(chunks); all_metadatas.extend(metadatas); success_count += 1

    await db.commit()
    if all_chunks: add_documents_to_faiss(chunks=all_chunks, metadatas=all_metadatas)
    return {"success": True, "message": "批量导入完成", "count": success_count}
