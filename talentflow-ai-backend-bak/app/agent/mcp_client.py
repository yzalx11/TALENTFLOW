# app/agent/mcp_client.py
"""
MCP Client — Agent 通过 MCP 协议调用 MCP Server 的工具
MCP Server 暴露: recommend_jobs, get_user_resume_info
"""
from fastmcp import Client as MCPClient
from app.core.logger import logger

MCP_SERVER_URL = "http://127.0.0.1:8002/sse"

_client = None


async def get_client() -> MCPClient:
    """全局单例，连接 MCP Server"""
    global _client
    if _client is None:
        _client = MCPClient(transport="sse")
        await _client.connect(MCP_SERVER_URL)
        logger.info(f"[MCP] 已连接: {MCP_SERVER_URL}")
    return _client


async def call_tool(name: str, **params) -> dict:
    """Agent 通过 MCP 协议调用工具"""
    try:
        client = await get_client()
        result = await client.call_tool(name, params)
        logger.info(f"[MCP] call_tool {name}({params}) → ok")
        return result
    except Exception as e:
        logger.error(f"[MCP] call_tool {name} failed: {e}")
        raise


async def recommend_jobs(user_id: int) -> dict:
    """通过 MCP 获取职位推荐"""
    result = await call_tool("recommend_jobs", user_id=user_id)
    content = result.content[0].text if hasattr(result, "content") else str(result)
    import json
    data = json.loads(content) if isinstance(content, str) else content
    return data.get("data", data) if isinstance(data, dict) else {}


async def get_user_resume(user_id: int) -> dict:
    """通过 MCP 获取用户简历"""
    result = await call_tool("get_user_resume_info", user_id=user_id)
    content = result.content[0].text if hasattr(result, "content") else str(result)
    import json
    return json.loads(content) if isinstance(content, str) else content
