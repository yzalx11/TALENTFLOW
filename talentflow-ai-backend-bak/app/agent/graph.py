# app/agent/graph.py
"""图编译 — 声明式定义 Agent 流程，导入 state/nodes/edges 组装"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agent.state import AgentState

# Memory Checkpointer — 当前 RedisSaver 不支持 ainvoke，暂用内存
checkpointer = MemorySaver()
from app.agent.nodes import (
    fetch_resume_node,
    get_recommendations_node,
    optimize_resume_node,
    save_optimized_resume_node,
    generate_letter_node,
    apply_jobs_node,
    save_record_node,
)
from app.agent.edges import route_after_fetch, route_after_recommend

# 预加载所有 model，避免节点内懒 import 时 SQLAlchemy 关系解析失败
import app.models.resume         
import app.models.resume_skill   
import app.models.skills         
import app.models.application    
import app.models.job_position   
import app.models.task           


def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("fetch_resume", fetch_resume_node)
    builder.add_node("get_recommendations", get_recommendations_node)
    builder.add_node("optimize_resume", optimize_resume_node)
    builder.add_node("save_optimized_resume", save_optimized_resume_node)
    builder.add_node("generate_letter", generate_letter_node)
    builder.add_node("apply_jobs", apply_jobs_node)
    builder.add_node("save_record", save_record_node)

    builder.set_entry_point("fetch_resume")

    builder.add_conditional_edges("fetch_resume", route_after_fetch, {
        "get_recommendations": "get_recommendations",
        "save_record": "save_record",
    })

    builder.add_conditional_edges("get_recommendations", route_after_recommend, {
        "optimize_resume": "optimize_resume",
        "save_record": "save_record",
    })

    builder.add_edge("optimize_resume", "save_optimized_resume")
    builder.add_edge("save_optimized_resume", "generate_letter")
    builder.add_edge("generate_letter", "apply_jobs")
    builder.add_edge("apply_jobs", "save_record")
    builder.add_edge("save_record", END)

    return builder.compile(checkpointer=checkpointer)


agent_graph = build_graph()
