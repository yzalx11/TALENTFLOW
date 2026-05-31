# app/rag/reranker.py
"""
交叉编码器精排 — 用 BGE-Reranker 对粗排结果做深度语义重排序
CrossEncoder 采用懒加载，避免 Celery Worker 启动时 segfault
"""
from app.core.config import settings
from app.core.logger import logger

DEFAULT_RERANKER_PATH = r"D:\py_lesson\RAG-Customer-Service\smart-cs-backend\app\rag\model\bge-reranker-v2-m3"


def _get_model_path() -> str:
    return settings.RERANKER_MODEL_PATH or DEFAULT_RERANKER_PATH

_reranker = None


def get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        model_path = _get_model_path()
        logger.info(f"⏳ 正在加载 Reranker 模型: {model_path}")
        _reranker = CrossEncoder(model_path)
        logger.info("✅ Reranker 模型加载完成")
    return _reranker


def rerank(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """
    对粗排候选做精排。

    Args:
        query: 用户简历摘要文本
        candidates: 粗排结果 [{title, description, score, ...}, ...]
        top_k: 最终返回数量

    Returns:
        精排后的 top_k 结果，score 为融合 reranker + 原始分的加权值
    """
    if not candidates:
        return []

    reranker = get_reranker()

    # 构建 (query, doc) 对
    pairs = []
    for c in candidates:
        doc = f"{c['title']} {c.get('description', '')}"[:2000]
        pairs.append([query, doc])

    try:
        scores = reranker.predict(pairs)
        if not isinstance(scores, list):
            scores = [scores]
    except Exception as e:
        logger.error(f"❌ Reranker 打分失败: {e}")
        return sorted(candidates, key=lambda x: x["score"], reverse=True)[:top_k]

    # 融合得分：70% reranker + 30% 原始分
    for i, c in enumerate(candidates):
        raw = c["score"] / 100.0
        c["score"] = round((0.7 * scores[i] + 0.3 * raw) * 100, 1)

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:top_k]
