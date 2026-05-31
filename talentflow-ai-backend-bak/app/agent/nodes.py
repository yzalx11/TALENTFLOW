# app/agent/nodes.py
"""Agent 节点 — 原子执行单元"""
from app.agent.state import AgentState
from app.core.logger import logger


async def fetch_resume_node(state: AgentState) -> dict:
    from app.core.database import SessionLocal
    from app.models.resume import Resume
    from sqlalchemy import select
    async with SessionLocal() as db:
        r = await db.execute(select(Resume).where(Resume.user_id == state["user_id"], Resume.is_default == 1, Resume.status == "reviewed"))
        resume = r.scalar()
        if not resume:
            r2 = await db.execute(select(Resume).where(Resume.user_id == state["user_id"], Resume.status == "reviewed").order_by(Resume.id.desc()).limit(1))
            resume = r2.scalar()
        if not resume:
            r3 = await db.execute(select(Resume).where(Resume.user_id == state["user_id"], Resume.status.in_(["processed", "reviewed"])).order_by(Resume.id.desc()).limit(1))
            resume = r3.scalar()
        if not resume:
            return {"error": "未找到已审核简历", "skip_generation": True}
        logger.info(f"[Agent] fetch_resume: user={state['user_id']}, resume_id={resume.id}")
        return {"resume": {"id": resume.id, "name": resume.name, "title": resume.title,
                           "skills": resume.skills or [], "summary": resume.summary or "",
                           "work_experience": resume.work_experience or "", "education": resume.education or ""}}


async def get_recommendations_node(state: AgentState) -> dict:
    import asyncio
    if state.get("skip_generation") or state.get("error"): return {}
    try:
        try:
            from app.agent.mcp_client import recommend_jobs as mcp_recommend
            result = await mcp_recommend(state["user_id"]); recs = result.get("recommendations", [])
        except Exception:
            from app.rag.recommendation import compute_recommendations
            result = await asyncio.to_thread(compute_recommendations, state["user_id"])
            recs = result.get("recommendations", [])
        threshold = state.get("threshold", 60)
        matched = [j for j in recs if j.get("score", 0) >= threshold]
        logger.info(f"[Agent] get_recommendations: total={len(recs)}, matched={len(matched)}")
        return {"recommendations": recs, "matched_jobs": matched}
    except Exception as e:
        logger.error(f"[Agent] get_recommendations failed: {e}")
        return {"error": str(e)}


async def optimize_resume_node(state: AgentState) -> dict:
    if state.get("skip_generation") or state.get("error"): return {}
    resume = state.get("resume", {}); matched = state.get("matched_jobs", [])
    if not resume or not matched: return {}
    try:
        from app.core.llm import get_llm
        llm = get_llm();
        if not llm: return {}
        skills = ", ".join(resume.get("skills", []))
        job_titles = ", ".join(j["title"] for j in matched[:3])
        from app.agent.skills import load_skill
        prompt = f"""{load_skill("optimize_resume")}

候选人技能: {skills}
经验: {resume.get('work_experience','')}
目标岗位: {job_titles}

只返回优化后的文本，不要额外说明。"""
        response = llm.invoke(prompt); optimized = response.content.strip().strip('"')
        logger.info("[Agent] optimize_resume: done")
        return {"optimized_summary": optimized}
    except Exception as e:
        logger.warning(f"[Agent] optimize_resume skipped: {e}")
        return {}


async def save_optimized_resume_node(state: AgentState) -> dict:
    optimized = state.get("optimized_summary", ""); resume = state.get("resume", {})
    if not optimized or not resume: return {}
    from app.core.database import SessionLocal
    from app.models.resume import Resume
    from sqlalchemy import select, update
    async with SessionLocal() as db:
        await db.execute(update(Resume).where(Resume.id == resume["id"]).values(summary=optimized))
        await db.commit()
        logger.info(f"[Agent] save_optimized_resume: resume_id={resume['id']}")
    return {}


async def generate_letter_node(state: AgentState) -> dict:
    if state.get("skip_generation") or state.get("error"): return {}
    resume = state.get("resume", {}); matched = state.get("matched_jobs", [])
    if not resume or not matched: return {}
    try:
        from app.core.llm import get_llm
        llm = get_llm();
        if not llm: return {"cover_letters": {}}
        skills = ", ".join(resume.get("skills", []))
        optimized = state.get("optimized_summary", resume.get("summary", ""))
        job_list = "\n".join(f"- {j['title']}: {j.get('description','')[:150]}" for j in matched[:3])
        from app.agent.skills import load_skill
        prompt = f"""{load_skill("generate_letter")}

候选人背景:
- 学历: {resume.get('education','')}
- 技能: {skills}
- 项目/工作经历: {resume.get('work_experience','')}
- 个人优势: {optimized}

目标岗位:
{job_list}"""
        response = llm.invoke(prompt); content = response.content.strip()
        if "```" in content: content = content.split("```")[1].split("```")[0]
        if content.startswith("json"): content = content[4:]
        import json; data = json.loads(content)
        cover_letters = data.get("cover_letters", {})
        logger.info(f"[Agent] generate_letter: {len(cover_letters)} letters")
        return {"cover_letters": cover_letters}
    except Exception as e:
        logger.warning(f"[Agent] generate_letter skipped: {e}")
        return {"cover_letters": {}}


async def apply_jobs_node(state: AgentState) -> dict:
    if state.get("error"): return {}
    matched = state.get("matched_jobs", [])
    if not matched: return {"applied": []}
    from app.core.database import SessionLocal
    from app.models.application import Application
    from sqlalchemy import select
    async with SessionLocal() as db:
        cover_letters = state.get("cover_letters", {})
        applied = []
        for job in matched:
            ex = await db.execute(select(Application.id).where(Application.user_id == state["user_id"], Application.job_id == job["job_id"]))
            if ex.scalar(): continue
            resume_id = state.get("resume", {}).get("id")
            letter = cover_letters.get(job["title"], "")
            app = Application(user_id=state["user_id"], job_id=job["job_id"], resume_id=resume_id, cover_letter=letter, status="applied")
            db.add(app); applied.append({"job_id": job["job_id"], "title": job["title"], "score": job["score"]})
        await db.commit()
        logger.info(f"[Agent] apply_jobs: applied {len(applied)} jobs")
        return {"applied": applied}


async def save_record_node(state: AgentState) -> dict:
    applied = state.get("applied", []); error = state.get("error")
    if error: logger.warning(f"[Agent] save_record: ended with error={error}")
    else: logger.info(f"[Agent] save_record: {len(applied)} jobs applied")
    return {}
