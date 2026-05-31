# app/agent/edges.py
"""条件路由函数 — Agent 逻辑判断"""
from app.agent.state import AgentState


def route_after_fetch(state: AgentState) -> str:
    """简历获取后决定: 有简历→推荐, 无简历→结束"""
    if state.get("skip_generation") or state.get("error"):
        return "save_record"
    return "get_recommendations"


def route_after_recommend(state: AgentState) -> str:
    """推荐后决定: 有匹配→优化, 无匹配→结束"""
    if state.get("error"):
        return "save_record"
    if not state.get("matched_jobs"):
        return "save_record"
    return "optimize_resume"


def route_after_optimize(state: AgentState) -> str:
    """优化后决定: 进入投递（优化失败也继续）"""
    return "apply_jobs"
