# app/core/llm.py
import json
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.core.logger import logger

# 单例模式：全局共享一个 LLM 客户端对象
_llm_instance = None

def get_llm():
    """获取大模型实例"""
    global _llm_instance
    if _llm_instance is None:
        if not settings.OPENAI_API_KEY:
            logger.error("❌ 未检测到 OPENAI_API_KEY，请检查 .env 文件")
            return None
            
        _llm_instance = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
            model="deepseek-chat",
            temperature=0.1,  # 降低随机性，保证提取的稳定性
            timeout=30        # 防止因网络波动导致死锁
        )
    return _llm_instance

async def analyze_job_skills(text: str) -> list[str]:
    """
    核心接口：解析职位文本，利用 LLM 提取技术栈标签
    """
    if not text or len(text.strip()) < 10:
        return []

    llm = get_llm()
    if not llm:
        return []

    # 精心设计的 Prompt：要求返回纯 JSON 列表
    prompt = f"""
    作为技术专家和高级 HR，请分析下方的职位描述内容，并精准提取该岗位要求的核心技术栈（如：Python, Java, Vue, PyTorch, RAG, MySQL 等）。

    要求：
    1. 仅提取技术相关的关键词。
    2. 必须以 JSON 数组格式返回，例如: ["Python", "Pandas", "Deep Learning"]。
    3. 不要输出任何额外的解释、Markdown 标记或代码块外框。

    职位描述：
    ---
    {text}
    ---
    """

    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()

        # 处理可能出现的 Markdown 代码块包裹
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        skills = json.loads(content)
        return skills if isinstance(skills, list) else []
        
    except Exception as e:
        logger.error(f"❌ LLM 提取技能时发生错误: {e}")
        return []
    
async def parse_job_full_info(text: str) -> dict:
    """
    全字段解析：将 JD 文本转换为结构化 JSON，用于前端自动填表
    """
    llm = get_llm()
    
    # 定义期望的 JSON 结构
    template = """
    你是一个专业的招聘数据提取助手。请从下方的职位描述文本中提取关键信息。
    要求：
    1. 必须返回严格的 JSON 格式。
    2. 如果某项未提及，请填入"未知"或空列表。
    3. 薪资请提取范围（如 15k-25k），如果没有则填"面议"。
    
    文本内容:
    {text}

    请输出以下格式的 JSON:
    {{
        "title": "职位名称",
        "company": "公司名称",
        "salary": "薪资范围",
        "location": "工作地点",
        "experience_requirement": "经验要求",
        "education_requirement": "学历要求",
        "required_skills": ["技能1", "技能2"],
        "description": "职位职责简述"
    }}
    """
    
    try:
        # 限制输入长度，防止 Token 溢出
        input_text = text[:2000]
        # 直接调用模型获取结果
        response = await llm.ainvoke(template.format(text=input_text))
        content = response.content.strip()
        
        # 清洗可能带有的 Markdown 标记
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        return json.loads(content)
    except Exception as e:
        logger.error(f"❌ LLM 全字段解析失败: {e}")
        return {}