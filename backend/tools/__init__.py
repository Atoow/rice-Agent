"""工具注册 —— 导出所有工具供 LangGraph ToolNode 使用。"""
from backend.tools.vector_search import vector_search
from backend.tools.graph_query import graph_query
from backend.tools.verify_claim import verify_claim
from backend.tools.calculator import calculator

# 所有 Function 类型工具列表（供 ToolNode 使用）
ALL_TOOLS = [
    vector_search,
    graph_query,
    verify_claim,
    calculator,
]

__all__ = ["ALL_TOOLS", "vector_search", "graph_query", "verify_claim", "calculator"]
