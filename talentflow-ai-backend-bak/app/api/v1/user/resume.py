# app/api/v1/user/resume.py
"""用户端简历管理 — 上传/解析/录入/更新/删除/设默认"""
from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.models.resume import Resume
from app.models.user import User
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.logger import logger
from app.core.llm import parse_resume_fields
from app.utils.file_parser import save_upload_file_to_disk, parse_resume_file

router = APIRouter(prefix="/api/v1/user", tags=["User-Resume"])


# ---- 上传文件 → AI 解析填表 ----
@router.post("/resumes/parse")
async def parse_resume(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    file_path = save_upload_file_to_disk(file)
    if not file_path: raise HTTPException(status_code=500, detail="文件保存失败")
    raw_text = parse_resume_file(file_path)
    if not raw_text: raise HTTPException(status_code=400, detail="未能提取文字内容")
    parsed = await parse_resume_fields(raw_text)
    return {"success": True, "data": parsed, "raw_text": raw_text}


# ---- 保存简历（含 AI 解析字段） ----
@router.post("/resumes")
async def create_resume(
    name: str = Form(...), title: Optional[str] = Form(None), phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None), education: Optional[str] = Form(None),
    experience: Optional[str] = Form(None), skills: Optional[str] = Form(None),
    summary: Optional[str] = Form(None), work_experience: Optional[str] = Form(None),
    project_experience: Optional[str] = Form(None), raw_text: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    import json as _json
    parsed_skills = []
    if skills:
        try: parsed_skills = _json.loads(skills)
        except: pass

    resume = Resume(
        user_id=current_user.id, name=name.strip(), title=title.strip() if title else None,
        phone=phone.strip() if phone else None, email=email.strip() if email else None,
        education=education.strip() if education else None, experience=experience.strip() if experience else None,
        skills=parsed_skills, summary=summary.strip() if summary else None,
        work_experience=work_experience.strip() if work_experience else None,
        project_experience=project_experience.strip() if project_experience else None,
        raw_text=raw_text.strip() if raw_text else None,
        status="processed" if raw_text else "pending",
    )

    # 第一份简历自动设为默认
    existing = await db.execute(select(Resume.id).where(Resume.user_id == current_user.id).limit(1))
    if existing.scalar() is None: resume.is_default = 1

    db.add(resume); await db.commit(); await db.refresh(resume)
    logger.info(f"✅ 用户 {current_user.id} 创建简历 ID={resume.id}")
    return {"id": resume.id, "name": resume.name, "title": resume.title, "status": resume.status}


# ---- 我的简历列表 ----
@router.get("/resumes")
async def list_my_resumes(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    resume_query = await db.execute(select(Resume).where(Resume.user_id == current_user.id).order_by(Resume.updated_at.desc()))
    resumes = resume_query.scalars().all()
    return [{
        "id": resume.id, "name": resume.name, "title": resume.title, "phone": resume.phone,
        "email": resume.email, "education": resume.education, "experience": resume.experience,
        "skills": resume.skills, "summary": resume.summary,
        "work_experience": resume.work_experience, "project_experience": resume.project_experience,
        "status": resume.status, "is_default": resume.is_default or 0,
        "created_at": str(resume.created_at) if resume.created_at else None,
        "updated_at": str(resume.updated_at) if resume.updated_at else None,
    } for resume in resumes]


# ---- 更新简历 ----
@router.put("/resumes/{resume_id}")
async def update_my_resume(
    resume_id: int, name: str = Form(...), title: Optional[str] = Form(None),
    phone: Optional[str] = Form(None), email: Optional[str] = Form(None),
    education: Optional[str] = Form(None), experience: Optional[str] = Form(None),
    skills: Optional[str] = Form(None), summary: Optional[str] = Form(None),
    work_experience: Optional[str] = Form(None), project_experience: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    import json as _json
    resume_query = await db.execute(select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id))
    resume = resume_query.scalar()
    if not resume: raise HTTPException(status_code=404, detail="简历不存在或无权操作")

    resume.name = name.strip()
    if title: resume.title = title.strip()
    if phone: resume.phone = phone.strip()
    if email: resume.email = email.strip()
    if education: resume.education = education.strip()
    if experience: resume.experience = experience.strip()
    if summary: resume.summary = summary.strip()
    if work_experience: resume.work_experience = work_experience.strip()
    if project_experience: resume.project_experience = project_experience.strip()
    if skills:
        try: resume.skills = _json.loads(skills)
        except: pass

    await db.commit()
    return {"id": resume.id, "name": resume.name, "title": resume.title, "status": resume.status}


# ---- 删除简历 ----
@router.delete("/resumes/{resume_id}")
async def delete_my_resume(resume_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    resume_query = await db.execute(select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id))
    resume = resume_query.scalar()
    if not resume: raise HTTPException(status_code=404, detail="简历不存在或无权操作")
    await db.delete(resume); await db.commit()
    return {"message": "简历已删除"}


# ---- 设为默认简历 ----
@router.post("/resumes/{resume_id}/default")
async def set_default_resume(resume_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    resume_query = await db.execute(select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id))
    resume = resume_query.scalar()
    if not resume: raise HTTPException(status_code=404, detail="简历不存在或无权操作")

    # 先清除其他默认
    all_user_resumes = await db.execute(select(Resume).where(Resume.user_id == current_user.id))
    for old in all_user_resumes.scalars().all(): old.is_default = 0
    resume.is_default = 1
    await db.commit()
    return {"message": f"已将「{resume.title or resume.name}」设为默认简历"}
