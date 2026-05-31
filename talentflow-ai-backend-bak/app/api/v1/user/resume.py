# app/api/v1/user/resume.py
"""
用户端简历管理 — 上传/解析/录入，自动绑定当前用户
"""
from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from sqlalchemy.orm import Session
from typing import Optional

from app.models.resume import Resume
from app.models.user import User
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.logger import logger
from app.core.llm import parse_resume_fields
from app.utils.file_parser import save_upload_file_to_disk, parse_resume_file

router = APIRouter(prefix="/api/v1/user", tags=["User-Resume"])


@router.post("/resumes/parse")
async def parse_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传简历文件，AI解析返回结构化JSON，不入库"""
    file_path = save_upload_file_to_disk(file)
    if not file_path:
        raise HTTPException(status_code=500, detail="文件保存失败")

    raw_text = parse_resume_file(file_path)
    if not raw_text:
        raise HTTPException(status_code=400, detail="未能提取文字内容")

    parsed = await parse_resume_fields(raw_text)
    return {"success": True, "data": parsed, "raw_text": raw_text}


@router.post("/resumes")
async def create_resume(
    name: str = Form(...),
    title: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    education: Optional[str] = Form(None),
    experience: Optional[str] = Form(None),
    skills: Optional[str] = Form(None, description="JSON数组字符串"),
    summary: Optional[str] = Form(None),
    work_experience: Optional[str] = Form(None),
    project_experience: Optional[str] = Form(None),
    raw_text: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """保存简历，自动绑定当前用户"""
    import json as _json
    parsed_skills = []
    if skills:
        try:
            parsed_skills = _json.loads(skills)
        except Exception:
            pass

    resume = Resume(
        user_id=current_user.id,
        name=name.strip(),
        title=title.strip() if title else None,
        phone=phone.strip() if phone else None,
        email=email.strip() if email else None,
        education=education.strip() if education else None,
        experience=experience.strip() if experience else None,
        skills=parsed_skills,
        summary=summary.strip() if summary else None,
        work_experience=work_experience.strip() if work_experience else None,
        project_experience=project_experience.strip() if project_experience else None,
        raw_text=raw_text.strip() if raw_text else None,
        status="processed" if raw_text else "pending",
    )
    # 第一份简历自动设为默认
    existing = db.query(Resume).filter(Resume.user_id == current_user.id).count()
    if existing == 0:
        resume.is_default = 1

    db.add(resume)
    db.commit()
    db.refresh(resume)
    logger.info(f"✅ 用户 {current_user.id} 创建简历 ID={resume.id}, is_default={resume.is_default}")
    return {"id": resume.id, "name": resume.name, "title": resume.title, "status": resume.status}


@router.get("/resumes")
def list_my_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的简历列表"""
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.updated_at.desc()).all()
    return [
        {"id": r.id, "name": r.name, "title": r.title, "phone": r.phone, "email": r.email,
         "education": r.education, "experience": r.experience,
         "skills": r.skills, "summary": r.summary,
         "work_experience": r.work_experience, "project_experience": r.project_experience,
         "status": r.status, "is_default": r.is_default or 0,
         "created_at": str(r.created_at) if r.created_at else None,
         "updated_at": str(r.updated_at) if r.updated_at else None}
        for r in resumes
    ]


@router.delete("/resumes/{resume_id}")
def delete_my_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除当前用户的简历"""
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在或无权操作")
    db.delete(resume)
    db.commit()
    return {"message": f"简历已删除"}


@router.post("/resumes/{resume_id}/default")
def set_default_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """设为默认简历（推荐/投递时优先使用）"""
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在或无权操作")

    # 先清除所有默认
    db.query(Resume).filter(Resume.user_id == current_user.id).update({"is_default": 0})
    # 设当前为默认
    resume.is_default = 1
    db.commit()
    return {"message": f"已将「{resume.title or resume.name}」设为默认简历"}
