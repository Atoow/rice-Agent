"""ReAct Agent 节点 —— 思考-行动-观察循环。
LLM 自主决定调用哪个工具，观察结果后继续推理，直到输出最终答案。
"""
import json
from backend.agent.state import AgentState
from backend.llm.prompts import REACT_SYSTEM_PROMPT
from backend.llm.factory import create_llm_provider
from backend.tools.vector_search import vector_search
from backend.tools.graph_query import graph_query
from backend.tools.verify_claim import verify_claim
from backend.tools.calculator import calculator

# 工具名 → 工具函数映射
TOOL_MAP = {
    "vector_search": vector_search,
    "graph_query": graph_query,
    "verify_claim": verify_claim,
    "calculator": calculator,
}


def _parse_react_output(text: str) -> dict:
    """解析 LLM 的 ReAct 格式输出。

    Returns:
        {
            "type": "action" | "answer" | "unknown",
            "tool": "tool_name",       # type=action 时
            "tool_input": "params",    # type=action 时
            "answer": "text",          # type=answer 时
        }
    """
    text = text.strip()
    lines = text.split("\n")

    result = {"type": "unknown"}

    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("Final Answer:") or line.startswith("最终答案：") or line.startswith("Final Answer："):
            answer = line.split(":", 1)[-1].strip() if ":" in line else line
            # 如果有多行，继续收集后续内容
            for j in range(i + 1, len(lines)):
                remaining = lines[j].strip()
                if remaining and not remaining.startswith(("Thought:", "Action:", "Final")):
                    answer += "\n" + remaining
            result["type"] = "answer"
            result["answer"] = answer
            return result

        if line.startswith("Action:") or line.startswith("行动：") or line.startswith("Action："):
            tool = line.split(":", 1)[-1].strip() if ":" in line else line
            result["tool"] = tool
            result["type"] = "action"
            continue

        if line.startswith("Action Input:") or line.startswith("行动输入：") or line.startswith("Action Input："):
            tool_input = line.split(":", 1)[-1].strip() if ":" in line else line
            result["tool_input"] = tool_input

    # 如果只找到 Action 但没 Action Input，尝试从整个文本中提取
    if result.get("type") == "action" and not result.get("tool_input"):
        # 看看 Thought 行中是否有参数
        for line in lines:
            if "搜索" in line or "查询" in line or "计算" in line or "验证" in line:
                result["tool_input"] = line.split("：", 1)[-1] if "：" in line else line.split(":", 1)[-1] if ":" in line else line
                break

    return result


def _execute_tool(tool_name: str, tool_input: str) -> str:
    """执行工具并返回观察结果。

    Args:
        tool_name: 工具名称
        tool_input: 原始参数字符串

    Returns:
        工具执行结果文本
    """
    tool = TOOL_MAP.get(tool_name)
    if not tool:
        return f"错误：未知工具 '{tool_name}'。可用工具：{', '.join(TOOL_MAP.keys())}"

    try:
        # 根据工具类型解析参数
        if tool_name == "vector_search":
            result = tool.invoke({"query": tool_input, "top_k": 3})
            if isinstance(result, list):
                lines = [f"[{r.get('source', '?')}, 相关度: {r.get('relevance', 0)}]\n{r['content'][:300]}" for r in result]
                return "\n\n".join(lines) if lines else "未找到相关内容"
            return str(result)

        elif tool_name == "graph_query":
            result = tool.invoke({"cypher": tool_input})
            if isinstance(result, dict) and result.get("error"):
                return f"图谱查询失败: {result['error']}"
            return json.dumps(result, ensure_ascii=False, indent=2)

        elif tool_name == "verify_claim":
            # parse "disease, symptom, control" format
            parts = [p.strip() for p in tool_input.split(",")]
            kwargs = {}
            if len(parts) >= 1:
                kwargs["disease"] = parts[0]
            if len(parts) >= 2:
                kwargs["symptom"] = parts[1]
            if len(parts) >= 3:
                kwargs["control"] = parts[2]
            result = tool.invoke(kwargs)
            return json.dumps(result, ensure_ascii=False, indent=2)

        elif tool_name == "calculator":
            # Try parsing as JSON or simple format
            try:
                params = json.loads(tool_input)
            except json.JSONDecodeError:
                params = {"input": tool_input}
            result = tool.invoke({"formula": tool_input.split(",")[0].strip(), "params": params})
            return json.dumps(result, ensure_ascii=False, indent=2)

        return str(result)

    except Exception as e:
        return f"工具执行错误: {str(e)}"


async def react_agent(state: AgentState) -> AgentState:
    """ReAct Agent 主节点 —— LLM 思考 + 决策下一步动作。

    这个节点只做推理，不执行工具。工具执行在 execute_tools 节点。
    通过 state["pending_action"] 传递待执行的工具信息。
    """
    state["react_loops"] = state.get("react_loops", 0) + 1
    llm = create_llm_provider()

    # 从 messages 构建对话历史
    conversation = ""
    for msg in state["messages"][-6:]:  # 最近 6 条
        role = msg.get("role", "user")
        content = msg.get("content", "")
        tag = msg.get("tag", "")  # ReAct tag: "action", "observation", etc.
        if tag:
            conversation += f"\n{content}\n"
        elif role == "user":
            conversation += f"\n用户: {content}\n"
        elif role == "assistant":
            conversation += f"\n助手: {content}\n"

    # 检查是否有工具观察结果待消化
    pending_observation = state.get("pending_observation", "")
    if pending_observation:
        conversation += f"\nObservation: {pending_observation}\n"
        state["pending_observation"] = ""  # 消费掉

    messages = [
        {"role": "system", "content": REACT_SYSTEM_PROMPT},
        {"role": "user", "content": f"对话历史：\n{conversation}\n\n请根据以上信息，输出你的下一步 Thought 和 Action，或者 Final Answer。"}
    ]

    response = await llm.generate(messages)

    if not response or not response.strip():
        # LLM 返回空，降级处理
        state["pending_action"] = None
        state["messages"].append({
            "role": "assistant",
            "content": "抱歉，我暂时无法处理这个问题，请换个方式提问。",
            "node_type": "react_agent"
        })
        state["node_events"].append({"node": "react_agent", "status": "complete", "data": {"type": "fallback"}})
        return state

    # 解析 ReAct 输出
    parsed = _parse_react_output(response)

    state["node_events"].append({
        "node": "react_agent",
        "status": "thinking",
        "data": {"response_preview": response[:100], "parsed_type": parsed["type"]}
    })

    if parsed["type"] == "action" and parsed.get("tool") in TOOL_MAP:
        # 需要执行工具
        state["pending_action"] = {
            "tool": parsed["tool"],
            "tool_input": parsed.get("tool_input", ""),
        }
        # 把 Thought 和 Action 记入对话
        action_msg = f"Thought: 我需要使用 {parsed['tool']}\nAction: {parsed['tool']}\nAction Input: {parsed.get('tool_input', '')}"
        state["messages"].append({"role": "assistant", "content": action_msg, "tag": "action"})
        state["node_events"].append({
            "node": "react_agent",
            "status": "action",
            "data": {"tool": parsed["tool"], "input": parsed.get("tool_input", "")[:50]}
        })

    elif parsed["type"] == "answer":
        # 最终答案
        state["pending_action"] = None
        state["messages"].append({
            "role": "assistant",
            "content": parsed["answer"],
            "node_type": "react_agent"
        })
        state["node_events"].append({
            "node": "react_agent",
            "status": "complete",
            "data": {"type": "answer", "length": len(parsed["answer"])}
        })

    else:
        # 无法解析，当作最终答案
        state["pending_action"] = None
        state["messages"].append({
            "role": "assistant",
            "content": response,
            "node_type": "react_agent"
        })
        state["node_events"].append({
            "node": "react_agent",
            "status": "complete",
            "data": {"type": "raw_response"}
        })

    return state


async def execute_tools(state: AgentState) -> AgentState:
    """执行工具节点 —— 调用 pending_action 指定的工具，将结果作为 Observation 传回。"""
    pending = state.get("pending_action", {})
    if not pending:
        state["node_events"].append({"node": "execute_tools", "status": "skip", "data": {}})
        return state

    tool_name = pending.get("tool", "")
    tool_input = pending.get("tool_input", "")

    state["node_events"].append({
        "node": "execute_tools",
        "status": "start",
        "data": {"tool": tool_name, "input": tool_input[:80]}
    })

    observation = _execute_tool(tool_name, tool_input)

    # 存储 observation，下一轮 react_agent 会消费
    state["pending_observation"] = observation

    state["node_events"].append({
        "node": "execute_tools",
        "status": "complete",
        "data": {"tool": tool_name, "observation_len": len(observation)}
    })

    return state
