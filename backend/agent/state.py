"""Agent 全局状态定义 —— 贯穿整个 LangGraph 状态图。"""
from typing import TypedDict


def _as_dict(msg) -> dict:
    """兼容 dict 和 LangChain Message 对象的取值辅助。"""
    if hasattr(msg, "content"):
        # LangChain Message 对象 (HumanMessage / AIMessage / SystemMessage)
        role = getattr(msg, "type", "unknown")
        content = msg.content
        extra = getattr(msg, "response_metadata", {}) or {}
        node_type = extra.get("node_type", "")
        return {"role": role, "content": content, "node_type": node_type}
    # 普通 dict
    return msg


def msg_get(msg, key: str, default=None):
    """从消息中取值，兼容 dict 和 LangChain Message 两种格式。"""
    d = _as_dict(msg)
    return d.get(key, default)


class AgentState(TypedDict):
    """Agent 推理过程中的完整状态。

    每个节点读取和修改此状态，状态在图的边之间传递。
    """
    # 对话（不使用 add_messages，保持 dict 格式，避免 HumanMessage 转换）
    messages: list[dict]

    # 意图路由
    intent: str  # "diagnose" | "knowledge" | "chitchat"

    # 诊断上下文（diagnose 分支使用）
    symptoms: list[str]               # 已收集的症状描述
    candidate_diseases: list[dict]    # 图谱候选病害
    # 每项格式: {"name": str, "scientific_name": str, "confidence": float, "matched_symptoms": [str]}

    # 置信度判断
    confidence: float                 # 当前诊断置信度 0.0-1.0
    missing_info: list[str]           # 还需追问的信息类型 ["环境条件", "品种", "近期天气"]
    clarify_count: int                # 已追问轮数

    # 验证 & 输出
    final_diagnosis: dict | None      # 最终诊断结果 {"disease": str, "reasoning": str, "plan": str}
    sources: list[dict]               # 知识来源追溯
    # 每项格式: {"content": str, "source": str, "relevance": float, "type": "vector"|"graph"}
    verification_result: dict | None  # 知识验证结果 {"valid": bool, "evidence": [...]}

    # 流式事件
    node_events: list[dict]           # 推送给前端的节点事件
    # 每项格式: {"node": str, "status": "start"|"complete", "data": dict}


def initial_state() -> AgentState:
    """创建初始空状态。"""
    return AgentState(
        messages=[],
        intent="",
        symptoms=[],
        candidate_diseases=[],
        confidence=0.0,
        missing_info=[],
        clarify_count=0,
        final_diagnosis=None,
        sources=[],
        verification_result=None,
        node_events=[],
    )
