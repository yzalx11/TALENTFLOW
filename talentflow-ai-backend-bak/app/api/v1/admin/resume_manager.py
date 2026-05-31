# app/api/v1/admin/resume_manager.py
"""
简历管理 API — 上传/解析/AI提取/列表/详情/审核
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status, Form, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String
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
from app.core.llm import parse_resume_fields
from app.rag.chain import extract_resume_skills

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-Resumes"])


def _build_resume_detail(resume: Resume, db: Session, include_all_skills: bool = False) -> dict:
    """将 Resume ORM 对象转为前端可用的字典"""
    # 关联的标准技能（从三表 join）
    standard_skills = (
        db.query(SkillDict)
        .join(ResumeSkill, ResumeSkill.skill_id == SkillDict.id)
        .filter(ResumeSkill.resume_id == resume.id)
        .all()
    )
    result = {
        # 旧表字段（前端直接使用）
        "id": resume.id,
        "name": resume.name,
        "phone": resume.phone,
        "email": resume.email,
        "title": resume.title,
        "education": resume.education,
        "experience": resume.experience,
        "skills": resume.skills or [],
        "summary": resume.summary,
        "project_experience": resume.project_experience,
        "work_experience": resume.work_experience,
        "source": resume.source,
        # PPT 管道字段
        "raw_text": resume.raw_text,
        "file_path": resume.file_path,
        "status": resume.status,
        # 标准化技能（三表关联结果）
        "standard_skills": [
            {"id": s.id, "standard_name": s.standard_name, "category": s.category}
            for s in standard_skills
        ],
        "created_at": str(resume.created_at) if resume.created_at else None,
        "updated_at": str(resume.updated_at) if resume.updated_at else None,
    }
    if include_all_skills:
        all_skills = db.query(SkillDict).order_by(SkillDict.category, SkillDict.standard_name).all()
        result["all_skills"] = [
            {"id": s.id, "standard_name": s.standard_name, "category": s.category}
            for s in all_skills
        ]
    return result


# ==========================================
# 1. 上传简历 → 解析 → AI提取 → 入库
# ==========================================
@router.post("/resumes/upload", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(..., description="简历文件 (PDF/DOCX/TXT)"),
    name: str = Form(..., description="候选人姓名"),
    title: Optional[str] = Form(None, description="意向职位"),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    education: Optional[str] = Form(None),
    experience: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """上传简历文件，自动解析文本并用 AI 提取技能"""
    logger.info(f"📥 接收简历: {file.filename}, 候选人: {name}")

    file_path = save_upload_file_to_disk(file)
    if not file_path:
        raise HTTPException(status_code=500, detail="文件保存失败")

    raw_text = parse_resume_file(file_path)
    if not raw_text:
        raw_text = ""

    resume = Resume(
        name=name.strip(),
        title=title.strip() if title else None,
        email=email.strip() if email else None,
        phone=phone.strip() if phone else None,
        education=education.strip() if education else None,
        experience=experience.strip() if experience else None,
        raw_text=raw_text,
        file_path=file_path,
        status="processed",
    )
    db.add(resume)
    db.flush()

    # AI 技能提取
    extracted_skills = []
    if raw_text and len(raw_text.strip()) >= 10:
        try:
            extracted_skills = await extract_resume_skills(raw_text, db)
        except Exception as e:
            logger.error(f"❌ AI 技能提取失败: {e}")

    # 写入标准化技能关联 + 同时更新 JSON skills 字段（兼容旧前端）
    skill_names = []
    for skill_name in extracted_skills:
        skill = db.query(SkillDict).filter(SkillDict.standard_name == skill_name).first()
        if skill:
            db.add(ResumeSkill(resume_id=resume.id, skill_id=skill.id))
            skill_names.append(skill_name)

    if skill_names:
        resume.skills = skill_names

    db.commit()
    db.refresh(resume)

    logger.info(f"✅ 简历入库完成: ID={resume.id}, 技能={skill_names}")
    return _build_resume_detail(resume, db)


# ==========================================
# 1b. 预解析接口 — 上传文件 → AI填表（不入库）
# ==========================================
@router.post("/resumes/parse")
async def parse_resume_for_form(
    file: UploadFile = File(..., description="简历文件 (PDF/DOCX/TXT)"),
    current_user: User = Depends(get_current_active_admin),
):
    """
    上传简历文件，AI 解析后返回结构化 JSON 用于前端自动填表。
    对标 /jobs/parse，仅供填表使用，不保存数据库。
    """
    logger.info(f"🤖 正在预解析简历: {file.filename}")

    file_path = save_upload_file_to_disk(file)
    if not file_path:
        raise HTTPException(status_code=500, detail="文件保存失败")

    raw_text = parse_resume_file(file_path)
    if not raw_text:
        raise HTTPException(status_code=400, detail="未能从文件中提取文字内容")

    parsed = await parse_resume_fields(raw_text)
    return {"success": True, "data": parsed, "raw_text": raw_text}


# ==========================================
# 1c. 纯表单创建 — 前端校对后提交入库（不含文件解析）
# ==========================================
@router.post("/resumes", status_code=status.HTTP_201_CREATED)
async def create_resume(
    name: str = Form(..., description="候选人姓名"),
    title: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    education: Optional[str] = Form(None),
    experience: Optional[str] = Form(None),
    skills: Optional[str] = Form(None, description="JSON数组字符串"),
    summary: Optional[str] = Form(None),
    work_experience: Optional[str] = Form(None),
    project_experience: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    raw_text: Optional[str] = Form(None, description="简历原始文本（AI解析时传入，用于技能标准化）"),
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """手动录入或AI解析校对后提交"""
    import json as _json

    parsed_skills = []
    if skills:
        try:
            parsed_skills = _json.loads(skills)
        except Exception:
            pass

    resume = Resume(
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
        source=source.strip() if source else "manual",
        status="processed" if raw_text else "pending",
    )
    db.add(resume)
    db.flush()

    # 如果有 raw_text，跑标准化技能提取
    if raw_text and len(raw_text.strip()) >= 10:
        try:
            std_skills = await extract_resume_skills(raw_text, db)
            skill_names = []
            for skill_name in std_skills:
                skill = db.query(SkillDict).filter(SkillDict.standard_name == skill_name).first()
                if skill:
                    db.add(ResumeSkill(resume_id=resume.id, skill_id=skill.id))
                    skill_names.append(skill_name)
            if skill_names:
                resume.skills = skill_names
            logger.info(f"🧠 标准化技能: {skill_names}")
        except Exception as e:
            logger.error(f"❌ 技能标准化失败: {e}")

    db.commit()
    db.refresh(resume)

    logger.info(f"✅ 简历录入: ID={resume.id}, status={resume.status}")
    return _build_resume_detail(resume, db)


# ==========================================
# 2. 简历列表
# ==========================================
@router.get("/resumes")
def list_resumes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None, description="搜索姓名/邮箱/职位"),
    status_filter: Optional[str] = Query(None, alias="status", description="按状态筛选"),
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Resume)
    if keyword:
        query = query.filter(
            or_(
                Resume.name.like(f"%{keyword}%"),
                Resume.email.like(f"%{keyword}%"),
                Resume.title.like(f"%{keyword}%"),
                cast(Resume.skills, String).like(f"%{keyword}%"),
            )
        )
    if status_filter:
        query = query.filter(Resume.status == status_filter)

    total = query.count()
    items = query.order_by(Resume.updated_at.desc()).offset(skip).limit(limit).all()

    return {
        "items": [_build_resume_detail(r, db) for r in items],
        "total": total,
    }


# ==========================================
# 2b. 更新简历
# ==========================================
@router.put("/resumes/{resume_id}")
def update_resume(
    resume_id: int,
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
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """更新简历基本信息"""
    import json as _json

    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    resume.name = name.strip()
    resume.title = title.strip() if title else None
    resume.phone = phone.strip() if phone else None
    resume.email = email.strip() if email else None
    resume.education = education.strip() if education else None
    resume.experience = experience.strip() if experience else None
    resume.summary = summary.strip() if summary else None
    resume.work_experience = work_experience.strip() if work_experience else None
    resume.project_experience = project_experience.strip() if project_experience else None

    if skills:
        try:
            resume.skills = _json.loads(skills)
        except Exception:
            pass

    db.commit()
    db.refresh(resume)
    logger.info(f"✅ 简历更新: ID={resume_id}")
    return _build_resume_detail(resume, db)


# ==========================================
# 3. 简历详情
# ==========================================
@router.get("/resumes/{resume_id}")
def get_resume_detail(
    resume_id: int,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    return _build_resume_detail(resume, db, include_all_skills=True)


# ==========================================
# 4. 审核提交
# ==========================================
@router.post("/resumes/{resume_id}/review")
def review_resume(
    resume_id: int,
    data: ResumeReviewSubmit,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """提交审核：写入确认的技能ID，同步更新 JSON skills，状态→reviewed"""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    # 删旧关联
    db.query(ResumeSkill).filter(ResumeSkill.resume_id == resume_id).delete()

    # 写新关联
    skill_names = []
    for skill_id in data.skill_ids:
        skill = db.query(SkillDict).filter(SkillDict.id == skill_id).first()
        if skill is None:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"技能ID {skill_id} 不存在")
        db.add(ResumeSkill(resume_id=resume_id, skill_id=skill_id))
        skill_names.append(skill.standard_name)

    # 同步 JSON skills 字段（兼容旧前端）
    resume.skills = skill_names
    resume.status = "reviewed"

    db.commit()
    db.refresh(resume)

    logger.info(f"✅ 简历审核完成: ID={resume_id}, 技能={skill_names}")
    return _build_resume_detail(resume, db)


# ==========================================
# 5. 删除简历
# ==========================================
@router.delete("/resumes/{resume_id}")
def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    db.delete(resume)
    db.commit()
    return {"message": f"简历 (ID: {resume_id}) 已删除"}
