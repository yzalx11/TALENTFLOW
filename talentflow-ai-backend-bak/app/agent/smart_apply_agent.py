# app/agent/smart_apply_agent.py
"""SmartApplyAgent — 封装 LangGraph + 状态 + 策略模式"""
from app.agent.graph import agent_graph
from app.core.logger import logger


class SmartApplyAgent:
    def __init__(self, user_id: int, mode: str = "auto", threshold: int = 60):
        self.user_id = user_id; self.mode = mode; self.threshold = threshold

    async def run(self) -> dict:
        if self.mode == "force_reuse":
            cached = await self._check_reuse()
            if cached: return cached

        state = {"user_id": self.user_id, "mode": self.mode, "threshold": self.threshold,
                 "skip_generation": self.mode == "force_reuse"}
        result = await agent_graph.ainvoke(state, config={"configurable": {"thread_id": str(self.user_id)}})
        return {"applied": result.get("applied", []), "error": result.get("error"),
                "cover_letters": result.get("cover_letters", {})}

    async def _check_reuse(self) -> dict | None:
        from app.core.database import SessionLocal
        from app.models.application import Application
        from app.models.resume import Resume
        from datetime import datetime, timedelta
        from sqlalchemy import select
        async with SessionLocal() as db:
            r = await db.execute(select(Resume).where(Resume.user_id == self.user_id, Resume.is_default == 1))
            resume = r.scalar()
            if not resume:
                r2 = await db.execute(select(Resume).where(Resume.user_id == self.user_id).order_by(Resume.id.desc()).limit(1))
                resume = r2.scalar()
            if not resume: return None
            since = datetime.utcnow() - timedelta(hours=24)
            r3 = await db.execute(select(Application).where(Application.user_id == self.user_id, Application.created_at >= since))
            apps = r3.scalars().all()
            if not apps: return None
            last_apply = max(a.created_at for a in apps)
            if resume.updated_at and resume.updated_at > last_apply: return None
            logger.info(f"[Agent] force_reuse: 命中 {len(apps)} 条当日投递")
            return {"applied": [{"job_id": a.job_id, "task_id": a.task_id, "status": a.status} for a in apps if a.job_id],
                    "error": None, "cover_letters": {}, "_reused": True}
