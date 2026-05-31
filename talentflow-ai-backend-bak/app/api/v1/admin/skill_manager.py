# app/api/v1/admin/skill_manager.py
"""
标准技能词典管理 — 维护 skills_dict 表，为 AI 提取提供封闭集合约束。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.models.skills import SkillDict
from app.models.user import User
from app.schemas.skills_schema import SkillDictCreate, SkillDictUpdate, SkillDictOut
from app.core.database import get_db
from app.core.deps import get_current_active_admin
from app.core.logger import logger

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-Skills"])


# ==========================================
# 工具函数：技能标准化（供 job/resume 端点调用）
# ==========================================
def standardize_skill_list(raw_skills: list[str], db: Session) -> list[str]:
    """
    将技能名称列表对照 skills_dict 做标准化。
    - 精确匹配 → 用标准名
    - 大小写不同 → 用标准名
    - 包含关系（如 "React" 匹配 "React.js"）→ 用标准名
    - 都不匹配 → 保留原名（可能是技能词典尚未收录的新技能）
    返回去重后的标准名称列表，保持原始顺序。
    """
    if not raw_skills:
        return []

    all_dict = db.query(SkillDict).all()
    if not all_dict:
        return list(dict.fromkeys(raw_skills))  # 词典为空，直接去重返回

    result = []
    for skill_name in raw_skills:
        name = skill_name.strip()
        if not name:
            continue

        matched = None

        # 1. 精确匹配
        for s in all_dict:
            if s.standard_name == name:
                matched = s.standard_name
                break

        # 2. 大小写不敏感匹配
        if matched is None:
            name_lower = name.lower()
            for s in all_dict:
                if s.standard_name.lower() == name_lower:
                    matched = s.standard_name
                    break

        # 3. 包含匹配（"React" 在 "React.js" 里，或反过来）
        if matched is None:
            name_lower = name.lower()
            for s in all_dict:
                std_lower = s.standard_name.lower()
                if name_lower in std_lower or std_lower in name_lower:
                    matched = s.standard_name
                    break

        # 4. 保留原名
        result.append(matched if matched else name)

    # 去重，保持顺序
    seen = set()
    unique = []
    for s in result:
        if s.lower() not in seen:
            seen.add(s.lower())
            unique.append(s)
    return unique


@router.get("/skills", response_model=list[SkillDictOut])
def list_skills(
    q: Optional[str] = Query(None, description="搜索标准技能名称"),
    category: Optional[str] = Query(None, description="按分类筛选"),
    skip: int = 0,
    limit: int = 500,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    query = db.query(SkillDict)
    if q:
        query = query.filter(SkillDict.standard_name.like(f"%{q}%"))
    if category:
        query = query.filter(SkillDict.category == category)
    return query.order_by(SkillDict.category, SkillDict.standard_name).offset(skip).limit(limit).all()


@router.post("/skills", response_model=SkillDictOut, status_code=status.HTTP_201_CREATED)
def create_skill(
    data: SkillDictCreate,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(SkillDict).filter(SkillDict.standard_name == data.standard_name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"技能 '{data.standard_name}' 已存在")

    skill = SkillDict(standard_name=data.standard_name, category=data.category)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    logger.info(f"✅ 新增标准技能: {skill.standard_name}")
    return skill


@router.put("/skills/{skill_id}", response_model=SkillDictOut)
def update_skill(
    skill_id: int,
    data: SkillDictUpdate,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    skill = db.query(SkillDict).filter(SkillDict.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    if data.standard_name is not None:
        conflict = db.query(SkillDict).filter(
            SkillDict.standard_name == data.standard_name,
            SkillDict.id != skill_id
        ).first()
        if conflict:
            raise HTTPException(status_code=400, detail=f"技能名称 '{data.standard_name}' 已被使用")
        skill.standard_name = data.standard_name

    if data.category is not None:
        skill.category = data.category

    db.commit()
    db.refresh(skill)
    return skill


@router.delete("/skills/{skill_id}")
def delete_skill(
    skill_id: int,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    skill = db.query(SkillDict).filter(SkillDict.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    db.delete(skill)
    db.commit()
    return {"message": f"技能 '{skill.standard_name}' 已删除"}
