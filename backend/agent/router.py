"""意图路由节点 —— 分类用户问题并设置后续路径。"""
from backend.agent.state import AgentState
from backend.llm.prompts import INTENT_ROUTE_PROMPT, format_prompt
from backend.llm.factory import create_llm_provider


async def intent_route(state: AgentState) -> AgentState:
    """分析用户意图，设置路由标签。

    将 intent 设为 "diagnose" / "knowledge" / "chitchat"。
    """
    llm = create_llm_provider()

    # 取最后一条用户消息
    user_msg = ""
    for msg in reversed(state["messages"]):
        if msg.get("role") == "user":
            user_msg = msg.get("content", "")
            break

    if not user_msg:
        state["intent"] = "chitchat"
        return state

    prompt = format_prompt(INTENT_ROUTE_PROMPT, question=user_msg)
    response = await llm.generate([{"role": "user", "content": prompt}])
    intent = response.strip().lower()

    # 规范化
    if "diagnose" in intent or "诊断" in intent:
        state["intent"] = "diagnose"
    elif "knowledge" in intent or "知识" in intent:
        state["intent"] = "knowledge"
    else:
        state["intent"] = "chitchat"
        # chitchat 分支直接走到 END，在此生成问候回复
        state["messages"].append({
            "role": "assistant",
            "content": "您好！我是水稻种植智能助手 🌾\n\n"
                       "我可以帮您：\n"
                       "• 诊断水稻病虫害（描述症状即可）\n"
                       "• 解答种植技术问题\n"
                       "• 查询品种特性和防治方法\n\n"
                       "请问有什么可以帮您的？",
            "node_type": "knowledge_answer",
        })

    state["node_events"].append({
        "node": "intent_route",
        "status": "complete",
        "data": {"intent": state["intent"]}
    })

    return state
