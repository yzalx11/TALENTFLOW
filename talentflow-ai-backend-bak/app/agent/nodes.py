# app/agent/nodes.py
"""
Agent 节点函数 — 每个节点是单一职责的原子执行单元

节点 = 执行单元（工人）
  输入: AgentState,全局黑板,读需要的字段
  输出: dict,局部更新，写回黑板

7 个节点按顺序：
  [1] fetch_resume           从数据库读取用户默认简历
  [2] get_recommendations    调推荐引擎（优先 MCP,fallback 直调）
  [3] optimize_resume        调 LLM.DeepSeek,优化简历亮点
  [4] save_optimized_resume  优化结果持久化到 resumes 表
  [5] generate_letter        调 LLM 生成个性化求职信
  [6] apply_jobs             逐岗位创建 Application 投递记录
  [7] save_record            记录最终日志（终态，无更新）
"""
from app.agent.state import AgentState
from app.core.logger import logger


# ==========================================
# [1] 查数据库，获取用户简历
# ==========================================
async def fetch_resume_node(state: AgentState) -> dict:
    from app.core.database import SessionLocal
    from app.models.resume import Resume
    from sqlalchemy import select

    async with SessionLocal() as db:
        # 优先：已审核 + 默认简历
        result = await db.execute(select(Resume).where(
            Resume.user_id == state["user_id"], Resume.is_default == 1, Resume.status == "reviewed"
        ))
        resume = result.scalar()

        # 降级：任意已审核简历
        if not resume:
            result = await db.execute(select(Resume).where(
                Resume.user_id == state["user_id"], Resume.status == "reviewed"
            ).order_by(Resume.id.desc()).limit(1))
            resume = result.scalar()

        # 再降级：已处理但未审核
        if not resume:
            result = await db.execute(select(Resume).where(
                Resume.user_id == state["user_id"], Resume.status.in_(["processed", "reviewed"])
            ).order_by(Resume.id.desc()).limit(1))
            resume = result.scalar()

        if not resume:
            return {"error": "未找到已审核简历", "skip_generation": True}

        logger.info(f"[Agent] fetch_resume: user={state['user_id']}, resume_id={resume.id}")
        return {"resume": {
            "id": resume.id, "name": resume.name, "title": resume.title,
            "skills": resume.skills or [], "summary": resume.summary or "",
            "work_experience": resume.work_experience or "", "education": resume.education or "",
        }}


# ==========================================
# 推荐引擎，取 Top-5 匹配岗位
# MCP 优先（Agent 协议调用），失败则 fallback 直调
# ==========================================
async def get_recommendations_node(state: AgentState) -> dict:
    import asyncio
    if state.get("skip_generation") or state.get("error"):
        return {}

    try:
        # MCP 协议通道
        try:
            from app.agent.mcp_client import recommend_jobs as mcp_recommend
            result = await mcp_recommend(state["user_id"])
            recs = result.get("recommendations", [])
        except Exception:
            # fallback 直调（MCP Server 不可用时）
            from app.rag.recommendation import compute_recommendations
            result = await asyncio.to_thread(compute_recommendations, state["user_id"])
            recs = result.get("recommendations", [])

        # 按阈值筛选匹配岗位
        threshold = state.get("threshold", 60)
        matched = [j for j in recs if j.get("score", 0) >= threshold]
        logger.info(f"[Agent] get_recommendations: total={len(recs)}, matched={len(matched)}")
        return {"recommendations": recs, "matched_jobs": matched}
    except Exception as e:
        logger.error(f"[Agent] get_recommendations failed: {e}")
        return {"error": str(e)}


# ==========================================
# LLM 优化简历亮点
# 调用 DeepSeek+技能+岗位标题 → 生成优化后的个人亮点
# 动态加载 Skills Prompt模板
# ==========================================
async def optimize_resume_node(state: AgentState) -> dict:
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

        prompt = f"""{load_skill("optimize_resume")}

候选人技能: {skills}
经验: {resume.get('work_experience', '')}
目标岗位: {job_titles}

只返回优化后的文本，不要额外说明。"""
        response = llm.invoke(prompt)
        optimized = response.content.strip().strip('"')
        logger.info("[Agent] optimize_resume: done")
        return {"optimized_summary": optimized}
    except Exception as e:
        logger.warning(f"[Agent] optimize_resume skipped: {e}")
        return {}


# ==========================================
# 优化结果持久化到数据库
# 写入 resumes.summary，下次 force_reuse 模式可跳过 LLM 生成
# ==========================================
async def save_optimized_resume_node(state: AgentState) -> dict:
    optimized = state.get("optimized_summary", "")
    resume = state.get("resume", {})
    if not optimized or not resume:
        return {}

    from app.core.database import SessionLocal
    from app.models.resume import Resume
    from sqlalchemy import update

    async with SessionLocal() as db:
        await db.execute(update(Resume).where(Resume.id == resume["id"]).values(summary=optimized))
        await db.commit()
        logger.info(f"[Agent] save_optimized_resume: resume_id={resume['id']}")
    return {}


# ==========================================
# LLM 生成个性化求职信
# 调用 DeepSeek + 学历/技能/项目经历/优化亮点 → 求职信 ×3
# 动态加载 Skills Prompt 模板
# ==========================================
async def generate_letter_node(state: AgentState) -> dict:
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
        experience = resume.get("work_experience", resume.get("summary", ""))

        job_list = "\n".join(
            f"- {j['title']}: {j.get('description', '')[:150]}"
            for j in matched  # 为所有匹配岗位生成求职信
        )
        from app.agent.skills import load_skill

        prompt = f"""{load_skill("generate_letter")}

候选人背景:
- 学历: {education}
- 技能: {skills}
- 项目/工作经历: {experience}
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


# ==========================================
# 逐个岗位创建投递记录
# ==========================================
async def apply_jobs_node(state: AgentState) -> dict:
    if state.get("error"):
        return {}

    matched = state.get("matched_jobs", [])
    if not matched:
        return {"applied": []}

    from app.core.database import SessionLocal
    from app.models.application import Application
    from sqlalchemy import select

    async with SessionLocal() as db:
        cover_letters = state.get("cover_letters", {})
        applied = []

        for job in matched:
            # 防重复投递
            existing = await db.execute(select(Application.id).where(
                Application.user_id == state["user_id"], Application.job_id == job["job_id"]
            ))
            if existing.scalar():
                continue

            resume_id = state.get("resume", {}).get("id")
            # 模糊匹配求职信 key（LLM 可能返回略有不同的标题）
            letter = cover_letters.get(job["title"], "")
            if not letter:
                for key, val in cover_letters.items():
                    if job["title"][:4] in key or key[:4] in job["title"]:
                        letter = val; break
            app = Application(
                user_id=state["user_id"], job_id=job["job_id"],
                resume_id=resume_id, cover_letter=letter, status="applied",
            )
            db.add(app)
            applied.append({"job_id": job["job_id"], "title": job["title"], "score": job["score"]})

        await db.commit()
        logger.info(f"[Agent] apply_jobs: applied {len(applied)} jobs")
        return {"applied": applied}


# ==========================================
# 记录执行日志
# ==========================================
async def save_record_node(state: AgentState) -> dict:
    applied = state.get("applied", [])
    error = state.get("error")
    if error:
        logger.warning(f"[Agent] save_record: ended with error={error}")
    else:
        logger.info(f"[Agent] save_record: {len(applied)} jobs applied")
    return {}  # 终态，无更新，Agent 流程结束
