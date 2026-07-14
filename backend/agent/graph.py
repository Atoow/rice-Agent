"""LangGraph 状态图 —— 编译 Agent 推理流程。"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from backend.agent.state import AgentState
from backend.agent.router import intent_route
from backend.agent.nodes.react_agent import react_agent, execute_tools
from backend.agent.nodes.collect import collect_info
from backend.agent.nodes.diagnose import check_confidence
from backend.agent.nodes.clarify import clarify
from backend.agent.nodes.verify import verify_claim_node
from backend.agent.nodes.generate import generate_plan, knowledge_answer
from backend.config import CONFIDENCE_THRESHOLD, MAX_CLARIFY_ROUNDS


# === 路由函数 ===

def route_after_intent(state: AgentState) -> str:
    """意图路由后的分支。diagnose 和 knowledge 都进入 ReAct 循环。"""
    intent = state.get("intent", "chitchat")
    if intent in ("diagnose", "knowledge"):
        return "react_agent"
    else:
        return "chitchat_end"


MAX_REACT_LOOPS = 8  # 防止死循环


def route_after_react(state: AgentState) -> str:
    """ReAct Agent 输出后的路由：继续执行工具 or 结束。"""
    loops = state.get("react_loops", 0)

    if loops >= MAX_REACT_LOOPS:
        return "force_end"

    if state.get("pending_action"):
        return "execute_tools"
    else:
        return "end"


def route_after_tools(state: AgentState) -> str:
    """工具执行后回到 ReAct Agent 继续推理。"""
    return "react_agent"


# === 状态图构建 ===

def build_graph() -> StateGraph:
    """构建并编译 Agent 状态图。

    Returns:
        编译后的 StateGraph，带 checkpoint 支持多轮对话恢复
    """
    workflow = StateGraph(AgentState)

    # ── 添加节点 ──
    workflow.add_node("intent_route", intent_route)
    workflow.add_node("react_agent", react_agent)
    workflow.add_node("execute_tools", execute_tools)

    # 入口
    workflow.set_entry_point("intent_route")

    # 意图路由
    workflow.add_conditional_edges(
        "intent_route",
        route_after_intent,
        {
            "react_agent": "react_agent",
            "chitchat_end": END,
        }
    )

    # ReAct 循环
    workflow.add_conditional_edges(
        "react_agent",
        route_after_react,
        {
            "execute_tools": "execute_tools",
            "end": END,
            "force_end": END,
        }
    )

    # 工具执行后回到 ReAct Agent（循环）
    workflow.add_edge("execute_tools", "react_agent")

    # 编译（带内存 checkpoint）
    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)

    return graph


# 模块级单例
_compiled_graph = None


def get_graph() -> StateGraph:
    """获取全局编译后的图实例。"""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
