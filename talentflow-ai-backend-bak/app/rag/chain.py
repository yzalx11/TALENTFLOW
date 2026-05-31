# app/rag/chain.py
"""
技能提取链 — 将 LLM 作为"标准化专员"，在封闭集合约束下将简历文本映射为标准技能名称。
核心思路
  1. 从 skills_dict 读取标准技能名称列表
  2. 技能词典较大时通过 retriever 做向量预过滤
  3. 将技能池 + 简历文本注入 Prompt temperature=0 消除随机性
  4. 强制 JSON 数组输出，仅返回标准列表中存在的项
"""
import json
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.logger import logger
from app.models.skills import SkillDict
from app.rag.retriver import prefilter_skills

# 技能提取专用 LLM 实例（temperature=0，与 core/llm.py 的通用实例隔离）
_extraction_llm: Optional[ChatOpenAI] = None


def _get_extraction_llm() -> Optional[ChatOpenAI]:
    """技能提取专用 LLM，temperature=0 确保确定性输出"""
    global _extraction_llm
    if _extraction_llm is not None:
        return _extraction_llm

    if not settings.OPENAI_API_KEY:
        logger.error("❌ OPENAI_API_KEY 未配置")
        return None

    _extraction_llm = ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE,
        model="deepseek-chat",
        temperature=0,
        timeout=30
    )
    return _extraction_llm


async def extract_resume_skills(
    resume_text: str,
    db_session,
    *,
    use_prefilter: bool = True,
    prefilter_k: int = 30,
    max_text_length: int = 3000,
    prefilter_threshold: int = 500,
) -> list[str]:
    """
    从简历文本中提取技能，映射到 skills_dict 中的标准名称。

    Args:
        resume_text: 简历原始文本
        db_session: SQLAlchemy 会话
        use_prefilter: 是否启用向量预过滤（仅当技能数 > prefilter_threshold 时触发）
        prefilter_k: 预过滤召回的候选技能数
        max_text_length: 送入 LLM 的简历文本最大长度
        prefilter_threshold: 触发预过滤的技能词典规模阈值

    Returns:
        匹配到的标准技能名称列表
    """
    if not resume_text or len(resume_text.strip()) < 10:
        return []

    # 1. 从数据库获取标准技能名称池
    all_skills = db_session.query(SkillDict).all()
    if not all_skills:
        logger.warning("⚠️ skills_dict 为空，无法提取技能")
        return []

    skill_pool = [s.standard_name for s in all_skills]

    # 2. 大规模词典时做向量预过滤
    if use_prefilter and len(skill_pool) > prefilter_threshold:
        candidates = prefilter_skills(resume_text, db_session, k=prefilter_k)
        if candidates:
            skill_pool = candidates

    # 3. 截断简历文本（技能描述通常在前半段）
    input_text = resume_text[:max_text_length]

    # 4. 构建结构化 Prompt
    skill_list_str = "\n".join(f"- {name}" for name in skill_pool)

    system_prompt = (
        "你是一位资深的技术招聘专家，擅长从简历中精准识别候选人的技术技能。\n"
        "你的任务是从简历文本中提取技能，并严格映射到下方提供的【标准技能列表】中。\n\n"
        "规则：\n"
        "1. 只能返回【标准技能列表】中存在的技能名称，禁止编造、改写或补充。\n"
        "2. 如果简历中的写法与标准名称不同但含义一致（如 Py→Python、SpringBoot→Spring Boot），"
        "请映射到标准名称。\n"
        "3. 只提取简历中明确提及的技能，不要推测或补充候选人可能具备的技能。\n"
        "4. 必须以纯 JSON 字符串数组格式返回，例如: [\"Python\", \"Django\", \"MySQL\"]。\n"
        "5. 不要输出任何解释、Markdown 标记、代码块或额外文字。"
    )

    user_prompt = (
        f"【标准技能列表】：\n{skill_list_str}\n\n"
        f"【简历文本】：\n{input_text}\n\n"
        f"请从标准技能列表中选出该候选人具备的技能，直接返回 JSON 数组。"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_prompt}"),
        ("human", "{user_prompt}"),
    ])

    # 5. 调用 LLM
    llm = _get_extraction_llm()
    if llm is None:
        return []

    chain = prompt | llm | StrOutputParser()

    try:
        response = await chain.ainvoke({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        })
        content = response.strip()

        # 清洗可能的 Markdown 包裹
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:]) if len(lines) > 1 else content
            if content.endswith("```"):
                content = content[:-3]
        if content.startswith("json"):
            content = content[4:]

        skills = json.loads(content)

        if not isinstance(skills, list):
            return []

        # 6. 兜底校验：过滤掉不在标准池中的幻觉输出
        valid_skills = [s for s in skills if s in skill_pool]
        if len(valid_skills) != len(skills):
            logger.warning(
                f"⚠️ LLM 返回了 {len(skills) - len(valid_skills)} 个非标准技能，已过滤"
            )

        return valid_skills

    except json.JSONDecodeError:
        logger.error(f"❌ LLM 返回非 JSON 格式: {content[:200]}")
        return []
    except Exception as e:
        logger.error(f"❌ 技能提取失败: {e}")
        return []
