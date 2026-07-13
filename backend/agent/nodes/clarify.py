"""追问澄清节点 —— 生成追问并暂停状态图等待用户回复。"""
from langgraph.types import interrupt
from backend.agent.state import AgentState
from backend.llm.prompts import CLARIFY_PROMPT, format_prompt
from backend.llm.factory import create_llm_provider


async def clarify(state: AgentState) -> AgentState:
    """生成追问问题，通过 LangGraph interrupt() 暂停并等待用户输入。

    interrupt() 会暂停状态图执行，将当前状态保存到 checkpoint。
    恢复时通过 Command(resume=用户回答) 继续执行，
    interrupt() 的返回值即为用户的新输入。
    """
    llm = create_llm_provider()

    prompt = format_prompt(
        CLARIFY_PROMPT,
        symptoms=str(state["symptoms"]),
        missing_info=str(state["missing_info"]),
        clarify_count=str(state["clarify_count"])
    )

    question = await llm.generate([{"role": "user", "content": prompt}])

    # 递增追问计数
    state["clarify_count"] = state.get("clarify_count", 0) + 1

    # 将追问写入 messages，前端展示给用户
    state["messages"].append({
        "role": "assistant",
        "content": question.strip(),
        "node_type": "clarify"  # 前端据此区分追问和最终回答
    })

    # 标记缺失信息为已知（简化处理，实际在 collect_info 中重新提取）
    state["missing_info"] = []

    state["node_events"].append({
        "node": "clarify",
        "status": "complete",
        "data": {"question": question.strip(), "round": state["clarify_count"]}
    })

    # === 暂停并等待用户回复 ===
    # interrupt() 会让状态图在此暂停，checkpoint 保存在 MemorySaver 中。
    # 当用户通过 chat API 再次发送消息时，使用 Command(resume=...) 恢复，
    # interrupt() 的返回值即为 resume 传入的内容（用户的新消息文本）。
    user_response = interrupt(state["messages"])

    # 提取用户回复内容（兼容 str / dict 两种格式）
    if isinstance(user_response, str):
        user_content = user_response
    elif isinstance(user_response, dict):
        user_content = user_response.get("content", str(user_response))
    else:
        user_content = str(user_response)

    # 将用户回复追加到消息历史，供 collect_info 下一轮提取症状
    state["messages"].append({
        "role": "user",
        "content": user_content,
    })

    return state
