# app/agent/state.py
"""AgentState — LangGraph 执行周期的全局共享黑板"""
from typing import TypedDict, Optional


class AgentState(TypedDict, total=False):
    user_id: int
    mode: str                          # auto / force_generate / force_reuse
    skip_generation: bool              # 缓存命中 → 跳过 LLM 生成

    resume: Optional[dict]             # 用户简历
    optimized_summary: str             # LLM 优化后的简历亮点
    recommendations: list[dict]        # 推荐岗位列表
    matched_jobs: list[dict]           # 得分 ≥ 阈值的岗位
    threshold: int                     # 最低匹配分（默认 60）

    applied: list[dict]                # 已投递结果
    cover_letters: dict                # job_id → 求职信
    error: Optional[str]               # 错误信息
