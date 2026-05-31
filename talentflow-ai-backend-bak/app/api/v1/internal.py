# app/api/v1/internal.py
"""
内部 API — Celery Worker 通过 HTTP 调用主进程的模型，避免 PyTorch 崩溃
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.embedding import get_embedding_function
from app.rag.reranker import get_reranker

router = APIRouter(prefix="/api/v1/internal", tags=["Internal"])


class EmbedRequest(BaseModel):
    texts: list[str]


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]


class RerankRequest(BaseModel):
    query: str
    candidates: list


class RerankResponse(BaseModel):
    scores: list[float]


@router.post("/embed", response_model=EmbedResponse)
def embed_texts(req: EmbedRequest):
    if not req.texts:
        return EmbedResponse(embeddings=[])

    try:
        embed_func = get_embedding_function()
        vectors = embed_func.embed_documents(req.texts)
        return EmbedResponse(embeddings=[v for v in vectors])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding 失败: {e}")


@router.post("/rerank", response_model=RerankResponse)
def rerank_candidates(req: RerankRequest):
    """
    交叉编码器精排。Worker 通过HTTP调用，避免子进程加载模型崩溃。
    """
    try:
        reranker = get_reranker()
        pairs = []
        for c in req.candidates:
            doc = f"{c.get('title', '')} {c.get('description', '')}"[:2000]
            pairs.append([req.query, doc])
        scores = reranker.predict(pairs)
        import numpy as np
        if isinstance(scores, np.ndarray):
            scores = scores.tolist()
        elif not isinstance(scores, list):
            scores = [scores]
        return RerankResponse(scores=[float(s) for s in scores])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rerank 失败: {e}")
