# app/agent/mcp_client.py
"""MCP Client — Agent 通过 MCP 协议调用 MCP Server 的工具"""
from fastmcp import Client
from app.core.logger import logger

MCP_SERVER_URL = "http://127.0.0.1:8003/mcp"


async def call_tool(name: str, **params) -> dict:
    """Agent 通过 MCP 协议调用工具"""
    try:
        async with Client(MCP_SERVER_URL) as client:
            result = await client.call_tool(name, params)
        logger.info(f"[MCP] call_tool {name}({params}) → ok")
        return result
    except Exception as e:
        logger.error(f"[MCP] call_tool {name} failed: {e}")
        raise


async def recommend_jobs(user_id: int) -> dict:
    result = await call_tool("recommend_jobs", user_id=user_id)
    content = result.content[0].text if hasattr(result, "content") else str(result)
    import json
    data = json.loads(content) if isinstance(content, str) else content
    return data.get("data", data) if isinstance(data, dict) else {}


async def get_user_resume(user_id: int) -> dict:
    result = await call_tool("get_user_resume_info", user_id=user_id)
    content = result.content[0].text if hasattr(result, "content") else str(result)
    import json
    return json.loads(content) if isinstance(content, str) else content
