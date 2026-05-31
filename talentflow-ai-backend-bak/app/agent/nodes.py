# app/agent/nodes.py
"""Agent 节点 — 每个函数是单一职责的原子执行单元"""
from app.agent.state import AgentState
from app.core.logger import logger


def fetch_resume_node(state: AgentState) -> dict:
    """获取用户默认简历"""
    from app.core.database import SessionLocal
    from app.models.resume import Resume

    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(
            Resume.user_id == state["user_id"],
            Resume.is_default == 1
        ).first()
        if not resume:
            resume = db.query(Resume).filter(
                Resume.user_id == state["user_id"]
            ).order_by(Resume.id.desc()).first()

        if not resume:
            return {"error": "未找到简历", "skip_generation": True}

        logger.info(f"[Agent] fetch_resume: user={state['user_id']}, resume_id={resume.id}")
        return {
            "resume": {
                "id": resume.id, "name": resume.name, "title": resume.title,
                "skills": resume.skills or [], "summary": resume.summary or "",
                "work_experience": resume.work_experience or "",
                "education": resume.education or "",
            }
        }
    finally:
        db.close()


async def get_recommendations_node(state: AgentState) -> dict:
    """获取职位推荐（MCP/直调 + run_in_executor）"""
    import asyncio

    if state.get("skip_generation") or state.get("error"):
        return {}

    try:
        # 尝试走 MCP
        try:
            from app.agent.mcp_client import recommend_jobs as mcp_recommend
            result = await mcp_recommend(state["user_id"])
            recs = result.get("recommendations", [])
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


def optimize_resume_node(state: AgentState) -> dict:
    """LLM 优化简历表述 — 针对目标岗位微调"""
    if state.get("skip_generation") or state.get("error"):
        return {}

    resume = state.get("resume", {})
    matched = state.get("matched_jobs", [])
    if not resume or not matched:
        return {}

    try:
        from app.core.llm import get_llm
        llm = get_llm()
        if not llm:
            return {}

        skills = ", ".join(resume.get("skills", []))
        job_titles = ", ".join(j["title"] for j in matched[:3])

        from app.agent.skills import load_skill
        skill_prompt = load_skill("optimize_resume")
        prompt = f"""{skill_prompt}

候选人技能: {skills}
经验: {resume.get('work_experience', '')}
目标岗位: {job_titles}

只返回优化后的文本，不要额外说明。"""

        response = llm.invoke(prompt)
        optimized = response.content.strip().strip('"')

        logger.info(f"[Agent] optimize_resume: done")
        return {"optimized_summary": optimized}
    except Exception as e:
        logger.warning(f"[Agent] optimize_resume skipped: {e}")
        return {}


def save_optimized_resume_node(state: AgentState) -> dict:
    """持久化 LLM 优化后的简历 — 供策略模式 reuse 命中"""
    optimized = state.get("optimized_summary", "")
    resume = state.get("resume", {})
    if not optimized or not resume:
        return {}

    from app.core.database import SessionLocal
    from app.models.resume import Resume
    db = SessionLocal()
    try:
        db.query(Resume).filter(Resume.id == resume["id"]).update({"summary": optimized})
        db.commit()
        logger.info(f"[Agent] save_optimized_resume: resume_id={resume['id']}")
    except Exception as e:
        db.rollback()
        logger.warning(f"[Agent] save_optimized_resume: {e}")
    finally:
        db.close()
    return {}


def generate_letter_node(state: AgentState) -> dict:
    """LLM 生成求职信 — 针对每个岗位"""
    if state.get("skip_generation") or state.get("error"):
        return {}

    resume = state.get("resume", {})
    matched = state.get("matched_jobs", [])
    if not resume or not matched:
        return {}

    try:
        from app.core.llm import get_llm
        llm = get_llm()
        if not llm:
            return {"cover_letters": {}}

        skills = ", ".join(resume.get("skills", []))
        optimized = state.get("optimized_summary", resume.get("summary", ""))
        education = resume.get("education", "")
        project = resume.get("work_experience", resume.get("summary", ""))
        job_list = "\n".join(
            f"- {j['title']}: {j.get('description','')[:150]}"
            for j in matched[:3]
        )

        from app.agent.skills import load_skill
        skill_prompt = load_skill("generate_letter")
        prompt = f"""{skill_prompt}

候选人背景:
- 学历: {education}
- 技能: {skills}
- 项目/工作经历: {project}
- 个人优势: {optimized}

目标岗位:
{job_list}"""

        response = llm.invoke(prompt)
        content = response.content.strip()
        if "```" in content:
            content = content.split("```")[1].split("```")[0]
        if content.startswith("json"):
            content = content[4:]

        import json
        data = json.loads(content)
        cover_letters = data.get("cover_letters", {})

        logger.info(f"[Agent] generate_letter: {len(cover_letters)} letters")
        return {"cover_letters": cover_letters}
    except Exception as e:
        logger.warning(f"[Agent] generate_letter skipped: {e}")
        return {"cover_letters": {}}


def apply_jobs_node(state: AgentState) -> dict:
    """逐个投递匹配的岗位"""
    if state.get("error"):
        return {}

    matched = state.get("matched_jobs", [])
    if not matched:
        return {"applied": []}

    from app.core.database import SessionLocal
    from app.models.application import Application

    db = SessionLocal()
    applied = []
    try:
        cover_letters = state.get("cover_letters", {})
        for job in matched:
            resume_id = state.get("resume", {}).get("id")
            letter = cover_letters.get(job["title"], "")
            app = Application(
                user_id=state["user_id"], job_id=job["job_id"],
                resume_id=resume_id, cover_letter=letter, status="applied"
            )
            db.add(app)
            applied.append({"job_id": job["job_id"], "title": job["title"], "score": job["score"]})

        db.commit()
        logger.info(f"[Agent] apply_jobs: applied {len(applied)} jobs")
        return {"applied": applied}
    except Exception as e:
        db.rollback()
        logger.error(f"[Agent] apply_jobs failed: {e}")
        return {"error": str(e), "applied": applied}
    finally:
        db.close()


def save_record_node(state: AgentState) -> dict:
    """持久化投递结果"""
    applied = state.get("applied", [])
    error = state.get("error")
    if error:
        logger.warning(f"[Agent] save_record: ended with error={error}")
    else:
        logger.info(f"[Agent] save_record: {len(applied)} jobs applied")
    return {}
