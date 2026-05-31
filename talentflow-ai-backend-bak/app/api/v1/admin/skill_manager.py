# app/api/v1/admin/skill_manager.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.models.skills import SkillDict
from app.models.user import User
from app.schemas.skills_schema import SkillDictCreate, SkillDictUpdate, SkillDictOut
from app.core.database import get_db
from app.core.deps import get_current_active_admin
from app.core.logger import logger

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-Skills"])


# ---- 工具函数：技能标准化（job_manager 复用） ----
def standardize_skill_list(raw_skills: list[str], db: AsyncSession) -> list[str]:
    """同步 helper——对照 skills_dict 映射到标准名称。返回去重后的标准名列表。"""
    # 当前为同步占位——完整逻辑待迁移
    return list(dict.fromkeys(raw_skills))


@router.get("/skills", response_model=list[SkillDictOut])
async def list_skills(
    q: Optional[str] = Query(None), category: Optional[str] = Query(None),
    skip: int = 0, limit: int = 500,
    current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db),
):
    conditions = []
    if q: conditions.append(SkillDict.standard_name.like(f"%{q}%"))
    if category: conditions.append(SkillDict.category == category)
    skills_query = await db.execute(
        select(SkillDict).where(*conditions)
        .order_by(SkillDict.category, SkillDict.standard_name)
        .offset(skip).limit(limit)
    )
    return skills_query.scalars().all()


@router.post("/skills", response_model=SkillDictOut, status_code=status.HTTP_201_CREATED)
async def create_skill(data: SkillDictCreate, current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(SkillDict.id).where(SkillDict.standard_name == data.standard_name))
    if existing.scalar(): raise HTTPException(status_code=400, detail=f"技能 '{data.standard_name}' 已存在")
    skill = SkillDict(standard_name=data.standard_name, category=data.category)
    db.add(skill); await db.commit(); await db.refresh(skill)
    return skill


@router.put("/skills/{skill_id}", response_model=SkillDictOut)
async def update_skill(skill_id: int, data: SkillDictUpdate,
                        current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db)):
    skill_query = await db.execute(select(SkillDict).where(SkillDict.id == skill_id))
    skill = skill_query.scalar()
    if not skill: raise HTTPException(status_code=404, detail="技能不存在")
    if data.standard_name and data.standard_name != skill.standard_name:
        conflict = await db.execute(select(SkillDict.id).where(
            SkillDict.standard_name == data.standard_name, SkillDict.id != skill_id
        ))
        if conflict.scalar(): raise HTTPException(status_code=400, detail="技能名称已被使用")
        skill.standard_name = data.standard_name
    if data.category: skill.category = data.category
    await db.commit(); await db.refresh(skill)
    return skill


@router.delete("/skills/{skill_id}")
async def delete_skill(skill_id: int, current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db)):
    skill_query = await db.execute(select(SkillDict).where(SkillDict.id == skill_id))
    skill = skill_query.scalar()
    if not skill: raise HTTPException(status_code=404, detail="技能不存在")
    await db.delete(skill); await db.commit()
    return {"message": "已删除"}
