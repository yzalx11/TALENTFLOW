# app/api/v1/admin/job_manager.py
from fastapi import APIRouter, Depends, HTTPException, Query, status, Form, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
import json
import time
import uuid

from app.models.job_position import JobPosition
from app.models.user import User
from app.schemas import job_schema
from app.core.database import get_db
from app.core.deps import get_current_active_admin
from app.core.logger import logger

from app.core.vector_store import add_documents_to_faiss

from app.core.llm import parse_job_full_info ,parse_multiple_jobs_info
from app.utils.file_parser import save_upload_file_to_disk, extract_text_from_local_file, split_text_pure_python
from app.api.v1.admin.skill_manager import standardize_skill_list

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-Jobs"])

# ==========================================
# 1. 预解析接口：专供前端“自动填表”使用
# ==========================================
@router.post("/jobs/parse")
async def parse_job_for_form(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_admin)
):
    """
    【预解析接口】仅供前端自动填表使用，不保存数据库
    """
    logger.info(f"🤖 正在为表单自动解析文档: {file.filename}")
    
    # 1. 临时保存并提取文字
    file_path = save_upload_file_to_disk(file)
    if not file_path:
        raise HTTPException(status_code=500, detail="文件上传失败")
        
    full_text = extract_text_from_local_file(file_path)
    
    # 2. 调用大模型进行全字段提取 (调用你 llm.py 里的函数)
    parsed_data = await parse_job_full_info(full_text)
    
    # 3. 直接返回提取出的 JSON
    return {
        "success": True,
        "data": parsed_data
    }

# ==========================================
# 2. 创建接口：正式保存入库
# ==========================================
@router.post("/jobs", response_model=job_schema.JobOut, status_code=status.HTTP_201_CREATED)
async def create_job(
    title: str = Form(...),
    company: str = Form(...),
    salary: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    experience_requirement: Optional[str] = Form(None),
    education_requirement: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    required_skills: Optional[str] = Form(None), 
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """【持久化】管理员确认并发布新职位 (MySQL + FAISS)"""
    try:
        # 1. 安全解析技能列表（增加类型校验）
        parsed_skills = []
        if required_skills:
            try:
                parsed_skills = json.loads(required_skills)
                parsed_skills = [
                    skill.strip()
                    for skill in parsed_skills
                    if isinstance(skill, str) and skill.strip()
                ]
                parsed_skills = standardize_skill_list(parsed_skills, db)
            except Exception as e:
                logger.error(f"解析技能列表失败: {e}, 原始值: {required_skills}")
                parsed_skills = []

        # 生成唯一JobID（避免并发重复）
        job_id = f"JOB-{uuid.uuid4().hex[:8]}"  # 替换原time.time()方式
        final_description = description or ""

        # 2. 安全处理上传文件（捕获文件处理异常）
        if file:
            logger.info(f"📥 接收职位文件: {file.filename}")
            try:
                file_path = save_upload_file_to_disk(file)
                if file_path:
                    full_text = extract_text_from_local_file(file_path, fallback_text=description or "")
                    final_description = final_description or full_text[:1000]
                    
                    # 文本切片（过滤空chunk）
                    document_chunks = split_text_pure_python(full_text, chunk_size=250, chunk_overlap=30)
                    document_chunks = [c.strip() for c in document_chunks if isinstance(c, str) and c.strip()]
                    
                    # 存入FAISS（仅当有有效chunk时）
                    if document_chunks:
                        metadatas = [{"job_id": job_id, "source_file": file.filename}] * len(document_chunks)
                        logger.info(f"🧠 存入FAISS: {len(document_chunks)}个Chunk")
                        add_documents_to_faiss(chunks=document_chunks, metadatas=metadatas)
            except Exception as e:
                logger.error(f"处理上传文件失败: {e}")
                # 不中断流程，仅跳过FAISS存储

        # 3. 存入MySQL（字段非空处理）
        new_job = JobPosition(
            job_id=job_id,
            title=title.strip(),
            company=company.strip(),
            salary=salary.strip() if salary else None,
            location=location.strip() if location else None,
            experience_requirement=experience_requirement.strip() if experience_requirement else None,
            education_requirement=education_requirement.strip() if education_requirement else None,
            description=final_description.strip() if final_description else None,
            required_skills=parsed_skills,
            is_active=True
        )
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        logger.info(f"✅ 职位创建成功: {job_id}")
        return new_job

    except Exception as e:
        # 数据库回滚 + 记录详细异常
        db.rollback()
        logger.error(f"创建职位失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建失败: {str(e)}"  # 前端可拿到具体错误
        )
# ==========================================
# 3. 列表接口
# ==========================================
@router.get("/jobs", response_model=List[job_schema.JobOut])
def read_jobs(
    skip: int = 0, limit: int = 100,
    keyword: Optional[str] = Query(None, description="搜索职位名称或公司"),
    is_active: Optional[bool] = Query(None, description="过滤有效职位"),
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    query = db.query(JobPosition)
    if keyword:
        query = query.filter(or_(JobPosition.title.like(f"%{keyword}%"), JobPosition.company.like(f"%{keyword}%")))
    if is_active is not None:
        query = query.filter(JobPosition.is_active == is_active)
    return query.offset(skip).limit(limit).all()

# ==========================================
# 4. 更新接口：全量字段更新
# ==========================================
@router.put("/jobs/{id}", response_model=job_schema.JobOut)
async def update_job(
    id: int,
    title: str = Form(...),
    company: str = Form(...),
    salary: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    experience_requirement: Optional[str] = Form(None),
    education_requirement: Optional[str] = Form(None),
    required_skills: str = Form("[]"),  
    description: str = Form(""),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    job = db.query(JobPosition).filter(JobPosition.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="职位不存在")

    # 1. 全量更新 MySQL 字段 [修复]
    job.title = title
    job.company = company
    job.salary = salary
    job.location = location
    job.experience_requirement = experience_requirement
    job.education_requirement = education_requirement
    job.description = description
    
    try:
        raw_skills = json.loads(required_skills)
        job.required_skills = standardize_skill_list(raw_skills, db)
    except:
        pass

    # 2. 如果重新上传了文件，追加到 FAISS [修复]
    if file:
        file_path = save_upload_file_to_disk(file)
        if file_path:
            full_text = extract_text_from_local_file(file_path)
            document_chunks = split_text_pure_python(full_text)
            metadatas = [{"job_id": job.job_id, "source_file": file.filename} for _ in document_chunks]
            if document_chunks:
                logger.info(f"🔄 更新职位，将新的 {len(document_chunks)} 个 Chunk 追加进 FAISS...")
                add_documents_to_faiss(chunks=document_chunks, metadatas=metadatas)

    db.commit()
    db.refresh(job)
    return job

# ==========================================
# 5. 删除接口
# ==========================================
@router.delete("/jobs/{id}")
def delete_job(
    id: int,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    job = db.query(JobPosition).filter(JobPosition.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="该职位记录不存在")
        
    db.delete(job)
    db.commit()
    return {"message": f"职位 (ID: {id}, JobID: {job.job_id}) 已成功删除"}


@router.post("/jobs/batch")
async def batch_import_jobs(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    【批量导入】上传包含多个岗位的长文档，AI 自动切分、解析并全部入库 (MySQL + FAISS)
    """
    logger.info(f"📥 正在批量处理职位文档: {file.filename}")
    
    # 1. 保存文件并提取所有文字
    file_path = save_upload_file_to_disk(file)
    if not file_path:
        raise HTTPException(status_code=500, detail="文件保存失败")
        
    full_text = extract_text_from_local_file(file_path)
    
    # 2. 召唤 LLM 进行批量切割提取
    jobs_data = await parse_multiple_jobs_info(full_text)
    
    if not jobs_data or not isinstance(jobs_data, list):
        raise HTTPException(status_code=400, detail="AI 未能从文档中成功提取到职位结构，请检查文档内容")

    # 3. 遍历提取到的列表，双轨入库 (MySQL 循环写，FAISS 攒起来批量写)
    success_count = 0
    all_chunks = []
    all_metadatas = []
    
    for job_info in jobs_data:
        # 为每个职位生成独立ID
        job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"
        
        # [A] 存入 MySQL
        new_job = JobPosition(
            job_id=job_id,
            title=job_info.get("title") or "未知职位",
            company=job_info.get("company") or "未知公司",
            salary=job_info.get("salary") or "面议",
            location=job_info.get("location") or "不限",
            experience_requirement=job_info.get("experience_requirement") or "不限",
            education_requirement=job_info.get("education_requirement") or "不限",
            description=job_info.get("description") or "",
            required_skills=job_info.get("required_skills") or [],
            is_active=True
        )
        db.add(new_job)
        
        # [B] 切片准备存入 FAISS
        desc_text = job_info.get("description", "")
        if not desc_text:
            desc_text = f"职位：{new_job.title}，技能：{', '.join(new_job.required_skills)}"
            
        chunks = split_text_pure_python(desc_text, chunk_size=250, chunk_overlap=30)
        metadatas = [{"job_id": job_id, "company": new_job.company, "source_file": file.filename} for _ in chunks]
        
        all_chunks.extend(chunks)
        all_metadatas.extend(metadatas)
        success_count += 1
        
    # 提交数据库事务
    db.commit()
    
    # 批量将所有切片丢进向量库
    if all_chunks:
        logger.info(f"🧠 正在将批量解析出的 {len(all_chunks)} 个 Chunk 存入 FAISS...")
        add_documents_to_faiss(chunks=all_chunks, metadatas=all_metadatas)
        
    return {
        "success": True,
        "message": f"批量导入完成",
        "count": success_count
    }