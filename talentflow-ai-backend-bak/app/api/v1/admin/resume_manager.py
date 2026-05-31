# app/api/v1/admin/resume_manager.py
"""管理员端 — 简历管理"""
from fastapi import APIRouter, Depends, HTTPException, Query, status, Form, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional

from app.models.resume import Resume
from app.models.resume_skill import ResumeSkill
from app.models.skills import SkillDict
from app.models.user import User
from app.schemas.resume_schema import ResumeReviewSubmit
from app.core.database import get_db
from app.core.deps import get_current_active_admin
from app.core.logger import logger
from app.utils.file_parser import save_upload_file_to_disk, parse_resume_file
from app.rag.chain import extract_resume_skills

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-Resumes"])


async def _build_resume_detail(resume: Resume, db: AsyncSession, include_all_skills: bool = False) -> dict:
    skill_query = await db.execute(select(SkillDict).join(ResumeSkill, ResumeSkill.skill_id == SkillDict.id).where(ResumeSkill.resume_id == resume.id))
    standard_skills = skill_query.scalars().all()

    detail = {
        "id": resume.id, "name": resume.name, "phone": resume.phone, "email": resume.email,
        "title": resume.title, "education": resume.education, "experience": resume.experience,
        "skills": resume.skills or [], "summary": resume.summary,
        "project_experience": resume.project_experience, "work_experience": resume.work_experience,
        "source": resume.source, "raw_text": resume.raw_text, "file_path": resume.file_path,
        "status": resume.status,
        "standard_skills": [{"id": s.id, "standard_name": s.standard_name, "category": s.category} for s in standard_skills],
        "created_at": str(resume.created_at) if resume.created_at else None,
        "updated_at": str(resume.updated_at) if resume.updated_at else None,
    }
    if include_all_skills:
        all_query = await db.execute(select(SkillDict).order_by(SkillDict.category, SkillDict.standard_name))
        detail["all_skills"] = [{"id": s.id, "standard_name": s.standard_name, "category": s.category} for s in all_query.scalars().all()]
    return detail


@router.post("/resumes/upload", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...), name: str = Form(...), title: Optional[str] = Form(None),
    email: Optional[str] = Form(None), phone: Optional[str] = Form(None),
    education: Optional[str] = Form(None), experience: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db),
):
    file_path = save_upload_file_to_disk(file)
    if not file_path: raise HTTPException(status_code=500, detail="文件保存失败")
    raw_text = parse_resume_file(file_path) or ""

    resume = Resume(name=name.strip(), title=title.strip() if title else None,
                    email=email.strip() if email else None, phone=phone.strip() if phone else None,
                    education=education.strip() if education else None, experience=experience.strip() if experience else None,
                    raw_text=raw_text, file_path=file_path, status="processed")
    db.add(resume); await db.flush()

    extracted_skills = []
    if raw_text and len(raw_text.strip()) >= 10:
        try: extracted_skills = await extract_resume_skills(raw_text, db)
        except Exception as e: logger.error(f"AI提取失败: {e}")

    for skill_name in extracted_skills:
        skill_query = await db.execute(select(SkillDict).where(SkillDict.standard_name == skill_name))
        skill = skill_query.scalar()
        if skill: db.add(ResumeSkill(resume_id=resume.id, skill_id=skill.id))

    if extracted_skills: resume.skills = extracted_skills
    await db.commit(); await db.refresh(resume)
    return await _build_resume_detail(resume, db)


@router.get("/resumes")
async def list_resumes(
    skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None), status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db),
):
    conditions = []
    if keyword: conditions.append(or_(Resume.name.like(f"%{keyword}%"), Resume.email.like(f"%{keyword}%"), Resume.title.like(f"%{keyword}%")))
    if status_filter: conditions.append(Resume.status == status_filter)

    count_query = await db.execute(select(func.count(Resume.id)).where(*conditions))
    total = count_query.scalar()

    resume_query = await db.execute(select(Resume).where(*conditions).order_by(Resume.updated_at.desc()).offset(skip).limit(limit))
    items = []
    for resume in resume_query.scalars().all():
        items.append(await _build_resume_detail(resume, db))
    return {"items": items, "total": total}


@router.get("/resumes/{resume_id}")
async def get_resume_detail(resume_id: int, current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db)):
    resume_query = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = resume_query.scalar()
    if not resume: raise HTTPException(status_code=404, detail="简历不存在")
    return await _build_resume_detail(resume, db, include_all_skills=True)


@router.post("/resumes/{resume_id}/review")
async def review_resume(
    resume_id: int, data: ResumeReviewSubmit,
    current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db),
):
    resume_query = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = resume_query.scalar()
    if not resume: raise HTTPException(status_code=404, detail="简历不存在")

    if data.action == "pass":
        old_skills = await db.execute(select(ResumeSkill).where(ResumeSkill.resume_id == resume_id))
        for old in old_skills.scalars().all(): await db.delete(old)

        skill_names = []
        for skill_id in data.skill_ids:
            skill_query = await db.execute(select(SkillDict).where(SkillDict.id == skill_id))
            skill = skill_query.scalar()
            if not skill: await db.rollback(); raise HTTPException(status_code=400, detail=f"技能ID {skill_id} 不存在")
            db.add(ResumeSkill(resume_id=resume_id, skill_id=skill_id))
            skill_names.append(skill.standard_name)
        resume.skills = skill_names
        resume.status = "reviewed"
    else:
        resume.status = "pending"

    await db.commit(); await db.refresh(resume)
    return await _build_resume_detail(resume, db)


@router.delete("/resumes/{resume_id}")
async def delete_resume(resume_id: int, current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db)):
    resume_query = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = resume_query.scalar()
    if not resume: raise HTTPException(status_code=404, detail="简历不存在")
    await db.delete(resume); await db.commit()
    return {"message": "简历已删除"}
