# app/agent/edges.py
"""
条件路由函数,根据运行时状态决定下一步走哪个节点

工作方式：
  - 输入当前 AgentState（黑板内容）
  - 检查关键字段（skip_generation, error, matched_jobs）
  - 返回下一个节点名称
"""
from app.agent.state import AgentState


def route_after_fetch(state: AgentState) -> str:
    """
     简历获取后决定去向
    """
    if state.get("skip_generation") or state.get("error"):
        return "save_record"
    return "get_recommendations"


def route_after_recommend(state: AgentState) -> str:
    """
    推荐完成后决定是否继续
    """
    if state.get("error"):
        return "save_record"
    if not state.get("matched_jobs"):
        return "save_record"
    return "optimize_resume"


def route_after_optimize(state: AgentState) -> str:
    """
    LLM 优化简历后直接去投递
    """
    return "apply_jobs"
