# app/agent/skills/__init__.py
"""动态加载 Skills Prompt 模板"""
import os

SKILLS_DIR = os.path.dirname(os.path.abspath(__file__))


def load_skill(name: str) -> str:
    """加载 skills/{name}.md，返回 Prompt 文本"""
    path = os.path.join(SKILLS_DIR, f"{name}.md")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
