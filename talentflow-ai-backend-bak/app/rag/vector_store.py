# app/rag/vector_store.py
"""
技能向量索引管理 — 将 skills_dict 中的标准技能名称嵌入为 FAISS 索引，
供 retriever 做语义预过滤，减少送入 LLM 的候选技能数量。
"""
import os
from langchain_community.vectorstores import FAISS
from app.core.embedding import get_embedding_function
from app.core.config import settings
from app.core.logger import logger

SKILL_INDEX_DIR = os.path.join(settings.VECTOR_DB_PATH, "skills")


def get_skill_index_path() -> str:
    return SKILL_INDEX_DIR


def build_skill_index(db_session) -> bool:
    """
    从 skills_dict 表读取所有标准技能名称，嵌入后构建 FAISS 索引。
    应在技能词典有更新后调用以保持索引同步。
    """
    from app.models.skills import SkillDict

    os.makedirs(SKILL_INDEX_DIR, exist_ok=True)

    skills = db_session.query(SkillDict).all()
    if not skills:
        logger.warning("⚠️ skills_dict 为空，无法构建技能索引")
        return False

    texts = [s.standard_name for s in skills]
    metadatas = [{"skill_id": s.id, "category": s.category or ""} for s in skills]

    try:
        embeddings = get_embedding_function()
        vector_store = FAISS.from_texts(
            texts=texts,
            embedding=embeddings,
            metadatas=metadatas
        )
        vector_store.save_local(SKILL_INDEX_DIR)
        logger.info(f"✅ 技能 FAISS 索引构建完成，共 {len(texts)} 条")
        return True
    except Exception as e:
        logger.error(f"❌ 技能索引构建失败: {e}")
        return False


def load_skill_index() -> FAISS | None:
    """加载已构建的技能 FAISS 索引，不存在则返回 None"""
    index_file = os.path.join(SKILL_INDEX_DIR, "index.faiss")
    if not index_file or not os.path.exists(index_file):
        return None

    embeddings = get_embedding_function()
    return FAISS.load_local(
        SKILL_INDEX_DIR,
        embeddings,
        allow_dangerous_deserialization=True
    )


def search_similar_skills(query_text: str, k: int = 30) -> list[dict]:
    """
    在技能向量索引中搜索与查询文本语义最相近的技能。
    返回 [{"skill_name": str, "skill_id": int, "category": str}, ...]
    """
    index = load_skill_index()
    if index is None:
        logger.warning("⚠️ 技能 FAISS 索引不存在，无法检索")
        return []

    docs = index.similarity_search(query_text, k=k)
    return [
        {
            "skill_name": doc.page_content,
            "skill_id": doc.metadata.get("skill_id"),
            "category": doc.metadata.get("category", "")
        }
        for doc in docs
    ]
