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
    
async def parse_resume_fields(text: str) -> dict:
    """
    简历全字段解析：从简历文本中提取结构化信息，用于前端自动填表。
    对标 parse_job_full_info，但针对简历场景设计输出字段。
    """
    llm = get_llm()
    if not llm:
        return {}

    template = """
你是一位资深的招聘专员。请从下方简历文本中提取关键信息，填入对应字段。

提取策略（请尽力推断，不要轻易放弃）：
- name: 简历开头或个人信息区的姓名。
- email: 包含 @ 的邮箱地址。
- phone: 11位手机号或座机号。
- title: 最近一份工作的职位名称（如"高级前端工程师"）；若无明确工作经历，则取简历标题或自我描述中暗示的职位方向。
- education: 最高学历（如"本科"、"硕士"、"博士"），可从学校信息或学历描述中推断。
- experience: 工作年限。
    优先：从工作经历的时间段计算总年限（如 2018-2023 → 5年）。
    其次：从简历中的自我描述提取（如"拥有8年开发经验"）。
    实在无法判断才留空。
- skills: 技术栈关键词列表，使用通用标准写法（Python 而非 py，React 而非 reactjs）。
- summary: 个人优势或自我评价的1-2句概括。
- work_experience: 工作经历部分的摘要，包含公司、职位、时间段。
- project_experience: 项目经验部分的摘要。

规则：
1. 必须返回严格的 JSON 格式，只输出 JSON，不要任何额外文字。
2. 只有经过充分尝试仍无法确定时，才填入空字符串 "" 或空列表 []。

简历文本:
{text}

JSON 格式:
{{
    "name": "...",
    "email": "...",
    "phone": "...",
    "title": "...",
    "education": "...",
    "experience": "...",
    "skills": ["...", "..."],
    "summary": "...",
    "work_experience": "...",
    "project_experience": "..."
}}
"""

    try:
        input_text = text[:4000]
        response = await llm.ainvoke(template.format(text=input_text))
        content = response.content.strip()

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return json.loads(content)
    except Exception as e:
        logger.warning(f"⚠️ LLM 简历字段解析失败: {e}")
        return {}


async def parse_multiple_jobs_info(text: str) -> list:
    """
    批量解析：从包含多个岗位的文档中提取出岗位列表
    """
    llm = get_llm()
    if not llm:
        return []
        
    template = """
    你是一个专业的招聘数据提取助手。请从下方的长文本中提取出【所有】提及的职位信息。
    文档中可能包含多个不同的职位。请将它们全部识别出来，并以严格的 JSON 数组 (Array) 格式返回。

    要求：
    1. 必须返回严格的 JSON 数组格式，每个元素是一个独立职位的 JSON 对象。
    2. 薪资请提取范围（如 15k-25k），没有则填"面议"。
    3. 如果某项未提及，请填入"不限"或空列表。

    文本内容:
    {text}

    请严格输出以下格式的 JSON 数组，不要包含任何其他说明文字:
    [
        {{
            "title": "职位名称1",
            "company": "公司名称",
            "salary": "薪资范围",
            "location": "工作地点",
            "experience_requirement": "经验要求",
            "education_requirement": "学历要求",
            "required_skills": ["技能A", "技能B"],
            "description": "职位职责和要求摘要"
        }},
        {{
            "title": "职位名称2",
            ...
        }}
    ]
    """
    
    try:
        # 批量文档通常比较长，这里放宽截断限制到 8000 字符（约 4000 个汉字）
        input_text = text[:8000]
        response = await llm.ainvoke(template.format(text=input_text))
        content = response.content.strip()
        
        # 清洗 Markdown 标记
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        parsed_data = json.loads(content)
        
        # 兜底容错处理
        if isinstance(parsed_data, list):
            return parsed_data
        elif isinstance(parsed_data, dict) and "jobs" in parsed_data:
            return parsed_data["jobs"]
        else:
            return [parsed_data] if isinstance(parsed_data, dict) else []
            
    except Exception as e:
        from app.core.logger import logger
        logger.error(f"❌ LLM 批量解析职位失败: {e}")
        return []