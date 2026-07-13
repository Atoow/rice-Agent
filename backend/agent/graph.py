"""LangGraph 状态图 —— 编译 Agent 推理流程。"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from backend.agent.state import AgentState
from backend.agent.router import intent_route
from backend.agent.nodes.collect import collect_info
from backend.agent.nodes.diagnose import check_confidence
from backend.agent.nodes.clarify import clarify
from backend.agent.nodes.verify import verify_claim_node
from backend.agent.nodes.generate import generate_plan, knowledge_answer
from backend.config import CONFIDENCE_THRESHOLD, MAX_CLARIFY_ROUNDS


# === 路由函数 ===

def route_after_intent(state: AgentState) -> str:
    """意图路由后的分支。"""
    intent = state.get("intent", "chitchat")
    if intent == "diagnose":
        return "collect_info"
    elif intent == "knowledge":
        return "knowledge_answer"
    else:
        return "chitchat_end"


def route_after_confidence(state: AgentState) -> str:
    """置信度判断后的分支。"""
    confidence = state.get("confidence", 0)
    clarify_count = state.get("clarify_count", 0)

    if confidence >= CONFIDENCE_THRESHOLD:
        return "verify_claim"
    elif clarify_count < MAX_CLARIFY_ROUNDS:
        return "clarify"
    else:
        # 追问已满，降级：直接生成方案，标记不确定性
        state["final_diagnosis"] = {
            "disease": "未能确诊",
            "confidence": confidence,
            "reasoning": f"追问 {clarify_count} 轮后仍无法确诊，基于现有信息给出建议"
        }
        return "verify_claim"


def route_after_clarify(state: AgentState) -> str:
    """追问后回到信息收集（等待用户下一轮输入）。"""
    return "collect_info"


# === 状态图构建 ===

def build_graph() -> StateGraph:
    """构建并编译 Agent 状态图。

    Returns:
        编译后的 StateGraph，带 checkpoint 支持多轮对话恢复
    """
    # 创建图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("intent_route", intent_route)
    workflow.add_node("collect_info", collect_info)
    workflow.add_node("check_confidence", check_confidence)
    workflow.add_node("clarify", clarify)
    workflow.add_node("verify_claim", verify_claim_node)
    workflow.add_node("generate_plan", generate_plan)
    workflow.add_node("knowledge_answer", knowledge_answer)

    # 入口
    workflow.set_entry_point("intent_route")

    # 边：意图路由
    workflow.add_conditional_edges(
        "intent_route",
        route_after_intent,
        {
            "collect_info": "collect_info",
            "knowledge_answer": "knowledge_answer",
            "chitchat_end": END,
        }
    )

    # 边：信息收集 → 置信度判断
    workflow.add_edge("collect_info", "check_confidence")

    # 边：置信度判断 → 验证 / 追问
    workflow.add_conditional_edges(
        "check_confidence",
        route_after_confidence,
        {
            "verify_claim": "verify_claim",
            "clarify": "clarify",
        }
    )

    # 边：追问 → 回到信息收集
    workflow.add_edge("clarify", "collect_info")

    # 边：验证 → 方案生成
    workflow.add_edge("verify_claim", "generate_plan")

    # 边：方案生成 → 结束
    workflow.add_edge("generate_plan", END)

    # 边：知识回答 → 结束
    workflow.add_edge("knowledge_answer", END)

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
