# app/rag/retriver.py
"""
技能预过滤器 — 对简历文本做向量检索，从技能词典中召回 Top-K 语义相近的候选技能，
将大规模技能词典缩减为 LLM 可处理的子集，降低 Token 消耗并提升映射准确率。
"""
from app.rag.vector_store import (
    search_similar_skills,
    build_skill_index,
    load_skill_index,
)
from app.core.logger import logger


def ensure_skill_index(db_session) -> bool:
    """
    确保技能 FAISS 索引存在，不存在则从 skills_dict 构建。
    在 extract_resume_skills 中首次调用时触发懒初始化。
    """
    if load_skill_index() is not None:
        return True

    logger.info("🆕 技能 FAISS 索引不存在，正在从 skills_dict 构建...")
    return build_skill_index(db_session)


def prefilter_skills(
    resume_text: str,
    db_session,
    k: int = 30
) -> list[str]:
    """
    输入简历文本，返回 Top-K 个语义最相近的标准技能名称列表。

    流程：
    1. 确保技能 FAISS 索引就绪
    2. 将简历文本 embedding 后在技能向量空间中检索
    3. 返回标准技能名称列表供 chain.py 注入 Prompt
    """
    if not resume_text or len(resume_text.strip()) < 10:
        return []

    if not ensure_skill_index(db_session):
        logger.warning("⚠️ 技能索引不可用，跳过预过滤")
        return []

    results = search_similar_skills(resume_text, k=k)
    skill_names = [r["skill_name"] for r in results]

    logger.info(f"🔍 技能预过滤: 从技能库中召回 {len(skill_names)} 个候选技能")
    return skill_names
