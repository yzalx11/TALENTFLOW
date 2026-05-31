# app/agent/graph.py
"""
LangGraph Agent 图编译 — 声明式定义智能投递的完整流程

图结构（7 节点 + 2 条件边 + 4 固定边）：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  START
    ↓
  [1] fetch_resume ──────→ 无简历/报错 ──→ [7] save_record
    │ 从数据库查默认简历                    ↑
    │      ↓ 有简历                         │
    │ [2] get_recommendations               │
    │ MCP 协议/直调推荐引擎                  │
    │      ↓ 有匹配岗位                      │
    │ [3] optimize_resume                   │
    │ LLM 优化简历亮点（DeepSeek）            │
    │      ↓                                │
    │ [4] save_optimized_resume             │
    │ 优化结果写回数据库，下次可复用           │
    │      ↓                                │
    │ [5] generate_letter                   │
    │ LLM 生成个性化求职信 ×3                 │
    │      ↓                                │
    │ [6] apply_jobs                        │
    │ 逐岗位创建 Application 投递记录         │
    │      ↓                                │
    └─────→ [7] save_record → END           │
            记录日志，持久化结果              │
              ↑ 已有/无匹配 ←─────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

边类型：
  - 条件边 (add_conditional_edges): 根据 state 动态决定下一步
  - 固定边 (add_edge): 永远按固定顺序执行
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agent.state import AgentState

# Memory Checkpointer — 断点续作，用户中断后可从此恢复
# 当前用内存实现，生产环境替换为 RedisSaver
checkpointer = MemorySaver()

from app.agent.nodes import (
    fetch_resume_node,          # [1] 查数据库，获取用户默认简历
    get_recommendations_node,   # [2] 调推荐引擎，取 Top-5 匹配岗位
    optimize_resume_node,       # [3] LLM 优化简历亮点，突出与岗位相关的技能
    save_optimized_resume_node, # [4] 优化结果写回 resumes 表，force_reuse 时可复用
    generate_letter_node,       # [5] LLM 针对前 3 个岗位生成个性化求职信
    apply_jobs_node,            # [6] 逐岗位创建 Application 记录，完成投递
    save_record_node,           # [7] 终态：记录日志
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
    """构建并编译 Agent 状态图"""
    builder = StateGraph(AgentState)

    # ==========================================
    # 注册节点（添加执行单元）
    # ==========================================
    builder.add_node("fetch_resume", fetch_resume_node)
    builder.add_node("get_recommendations", get_recommendations_node)
    builder.add_node("optimize_resume", optimize_resume_node)
    builder.add_node("save_optimized_resume", save_optimized_resume_node)
    builder.add_node("generate_letter", generate_letter_node)
    builder.add_node("apply_jobs", apply_jobs_node)
    builder.add_node("save_record", save_record_node)

    # ==========================================
    # 入口
    # ==========================================
    builder.set_entry_point("fetch_resume")

    # ==========================================
    # 条件边 — 根据运行时 state 动态决定分支
    # ==========================================

    # 条件边 : 简历获取后
    #   有简历 → 去推荐引擎
    #   无简历/出错 → 直接结束
    builder.add_conditional_edges("fetch_resume", route_after_fetch, {
        "get_recommendations": "get_recommendations",
        "save_record": "save_record",
    })

    # 条件边 : 推荐完成后
    #   有 ≥60 分的匹配岗位 → 去简历优化
    #   无匹配 → 直接结束
    builder.add_conditional_edges("get_recommendations", route_after_recommend, {
        "optimize_resume": "optimize_resume",
        "save_record": "save_record",
    })

    # 固定边 — 确定性顺序，不分支
    # LLM 优化简历 → 持久化优化结果（写入数据库）
    builder.add_edge("optimize_resume", "save_optimized_resume")
    # LLM 生成求职信
    builder.add_edge("save_optimized_resume", "generate_letter")
    # 逐岗位投递
    builder.add_edge("generate_letter", "apply_jobs")

    # 记录日志，结束流程
    builder.add_edge("apply_jobs", "save_record")

    #终止
    builder.add_edge("save_record", END)

    #编译图
    return builder.compile(checkpointer=checkpointer)


# 全局单例供 SmartApplyAgent 调用
agent_graph = build_graph()
