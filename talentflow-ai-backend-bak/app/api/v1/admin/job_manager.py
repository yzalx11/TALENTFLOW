# app/api/v1/admin/job_manager.py
from fastapi import APIRouter, Depends, HTTPException, Query, status ,Form, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

import json
import time

from app.models.job_position import JobPosition
from app.models.user import User
from app.schemas import job_schema
from app.core.database import get_db
from app.core.deps import get_current_active_admin
from app.utils.file_parser import extract_text_from_upload
from app.core.embedding import get_embedding_function
from app.core.logger import logger
from app.core.llm import analyze_job_skills
from app.core.vector_store import add_documents_to_faiss

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-Jobs"])

@router.post("/jobs", response_model=job_schema.JobOut, status_code=status.HTTP_201_CREATED)
async def create_job(
    # 使用 Form(...) 接收表单里的文字字段
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
    """
    管理员发布新职位 (支持 FormData 和 文件上传)
    """
    # 1. 还原前端发过来的技能列表
    parsed_skills = []
    if required_skills:
        try:
            # 将前端传来的 "['Vue', 'Python']" 字符串变回 Python 的 List
            parsed_skills = json.loads(required_skills)
        except:
            parsed_skills = []

    # 2. 自动生成一个业务职位 ID
    job_id = f"JOB-{int(time.time())}"

    # 3. 【文件处理预留位】
    document_chunks = []
    full_text = ""
    
    if file:
        logger.info(f"📥 接收到文件: {file.filename}, 开始解析...")
        
        # 3.1 统一解析为纯文本
        full_text = await extract_text_from_upload(file)
        
        if full_text:
            logger.info(f"✅ 文件解析成功，提取到 {len(full_text)} 个字符。")
            
            # 3.2 文本切分 (Chunking) - 为下一步存入向量数据库做准备
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=250,     
                chunk_overlap=30,   
                separators=["\n\n", "\n", "。", "！", "?", "，", "、", " "]
            )
            document_chunks = text_splitter.split_text(full_text)
            logger.info(f"🔪 文本已切分为 {len(document_chunks)} 个 Chunk。")
            # 3.2 构造元数据 (Metadata) 
            # 把每个文本块和当前的职位 ID 绑定，这样以后大模型搜索时，才知道这段话是哪个职位里的
            #metadatas = [{"job_id": job_id, "source_file": file.filename} for _ in document_chunks]
            
            # 3.3 存入 FAISS 向量数据库！
            logger.info("🧠 正在生成向量并存入 FAISS 数据库...")
            #add_documents_to_faiss(chunks=document_chunks, metadatas=metadatas)
    
            extracted_skills = await analyze_job_skills(full_text[:2000])
            
            # 合并手动填写的技能与 AI 提取的技能
            manual_skills = json.loads(required_skills) if required_skills else []
            final_skills = list(set(manual_skills + extracted_skills))
            
    # 4. 存入数据库
    new_job = JobPosition(
        job_id=job_id,
        title=title,
        company=company,
        salary=salary,
        location=location,
        experience_requirement=experience_requirement,
        education_requirement=education_requirement,
        description=description,
        required_skills=parsed_skills,
        is_active=True
    )
    
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
    
    # 模糊搜索
    if keyword:
        query = query.filter(
            or_(
                JobPosition.title.like(f"%{keyword}%"),
                JobPosition.company.like(f"%{keyword}%"),
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