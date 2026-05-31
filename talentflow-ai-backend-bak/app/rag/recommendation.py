# app/services/recommendation.py
"""
AI 职位推荐引擎 — 混合检索 + 加权打分 + Celery 异步任务
Embedding 通过 HTTP 调主进程 /internal/embed，避免 Worker 加载 PyTorch 崩溃。
"""
import requests
import numpy as np
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.logger import logger
from app.models.job_position import JobPosition
from app.models.resume import Resume
from app.models.resume_skill import ResumeSkill
from app.models.skills import SkillDict
import os as _os
BACKEND_HOST = _os.getenv("BACKEND_HOST", "127.0.0.1")
EMBED_URL = f"http://{BACKEND_HOST}:8000/api/v1/internal/embed"
RERANK_URL = f"http://{BACKEND_HOST}:8000/api/v1/internal/rerank"


def _rerank_via_http(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """HTTP 调用主进程的 Reranker 模型做精排"""
    if not candidates:
        return []
    try:
        resp = requests.post(RERANK_URL, json={"query": query, "candidates": candidates}, timeout=30)
        resp.raise_for_status()
        scores = resp.json()["scores"]
        # 批内归一化到 0~1
        min_s, max_s = min(scores), max(scores)
        if max_s > min_s:
            scores = [(s - min_s) / (max_s - min_s) for s in scores]
        else:
            scores = [0.5] * len(scores)
        for i, c in enumerate(candidates):
            raw = c["score"] / 100.0
            c["score"] = round((0.7 * scores[i] + 0.3 * raw) * 100, 1)
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_k]
    except Exception as e:
        logger.error(f"❌ Rerank HTTP 调用失败: {e}")
        return sorted(candidates, key=lambda x: x["score"], reverse=True)[:top_k]


def _embed_batch(texts: list[str]) -> list[np.ndarray]:
    """批量向量化 — HTTP 调主进程"""
    if not texts:
        return []
    try:
        resp = requests.post(EMBED_URL, json={"texts": texts}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return [np.array(v) for v in data["embeddings"]]
    except Exception as e:
        logger.error(f"❌ Embedding API 调用失败: {e}")
        raise


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def _jaccard_similarity(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _get_user_skills(resume: Resume, db: Session) -> set[str]:
    skills = set()
    std_skills = (
        db.query(SkillDict.standard_name)
        .join(ResumeSkill, ResumeSkill.skill_id == SkillDict.id)
        .filter(ResumeSkill.resume_id == resume.id)
        .all()
    )
    for (s,) in std_skills:
        skills.add(s.lower())
    for s in (resume.skills or []):
        skills.add(s.lower())
    return skills


def _build_query_text(resume: Resume) -> str:
    parts = [resume.title or "", resume.summary or "", resume.work_experience or ""]
    return " ".join([p for p in parts if p]) or resume.name or ""


@celery_app.task(bind=True, max_retries=2, default_retry_delay=5)
def compute_recommendations(self, user_id: int):
    """
    Celery 异步任务：为用户计算职位推荐。
    缓存策略：简历 + 岗位都没变 → 直接返回上次结果。
    """
    import redis as _redis
    import os
    cache = _redis.Redis.from_url(f"{_os.getenv('REDIS_URL', 'redis://127.0.0.1:6379')}/2")

    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.user_id == user_id, Resume.is_default == 1).first()
        if not resume:
            resume = db.query(Resume).filter(Resume.user_id == user_id).order_by(Resume.id.desc()).first()
        if not resume:
            return {"error": "未找到简历，请先上传简历", "recommendations": []}

        # 检查缓存：简历ID + 岗位最新更新时间 都没变 → 命中
        job_max_ts = db.query(JobPosition.updated_at).filter(JobPosition.is_active == True).order_by(JobPosition.updated_at.desc()).first()
        job_max_ts = str(job_max_ts[0]) if job_max_ts and job_max_ts[0] else "0"
        cache_key = f"rec:{user_id}:{resume.id}:{job_max_ts}"

        cached = cache.get(cache_key)
        if cached:
            import json as _json
            logger.info(f"💨 推荐缓存命中: {cache_key}")
            return _json.loads(cached)

        user_skills = _get_user_skills(resume, db)
        query_text = _build_query_text(resume)

        jobs = db.query(JobPosition).filter(JobPosition.is_active == True).all()
        if not jobs:
            return {"error": "暂无可用职位", "recommendations": []}

        # 批量 embedding：简历查询 + 所有职位文本
        job_texts = [f"{j.title} {j.description or ''}"[:2000] for j in jobs]
        all_texts = [query_text] + job_texts
        all_vecs = _embed_batch(all_texts)
        query_vec = all_vecs[0]
        job_vecs = all_vecs[1:]

        results = []
        for i, job in enumerate(jobs):
            job_skills = {s.lower() for s in (job.required_skills or [])}
            jaccard = _jaccard_similarity(user_skills, job_skills)
            cosine = _cosine_similarity(query_vec, job_vecs[i])
            score = round((0.7 * cosine + 0.3 * jaccard) * 100, 1)
            matched = [s for s in user_skills if s in job_skills]

            results.append({
                "job_id": job.id,
                "title": job.title,
                "company": job.company,
                "salary": job.salary,
                "location": job.location,
                "score": score,
                "matched_skills": matched,
                "required_skills": list(job_skills),
                "description": (job.description or "")[:200],
            })

        # 4. 粗排 → 精排：Top-15 送 Reranker（HTTP） → Top-5
        results.sort(key=lambda x: x["score"], reverse=True)
        coarse_top = results[:15]  # PPT: max_rerank_limit

        final = _rerank_via_http(query_text, coarse_top, top_k=5)
        result = {"recommendations": final if final else coarse_top[:5]}

        import json as _json
        cache.setex(cache_key, 3600, _json.dumps(result, ensure_ascii=False))

        logger.info(f"✅ 推荐完成: user_id={user_id}, top={[(r['title'], r['score']) for r in result['recommendations']]}")
        return result

    except Exception as e:
        logger.error(f"❌ 推荐任务失败: {e}")
        try:
            self.retry(exc=e)
        except Exception:
            pass
        return {"error": str(e), "recommendations": []}
    finally:
        db.close()
