"""信息收集节点 —— 从用户消息提取症状 + 图谱查询候选病害。"""
from backend.agent.state import AgentState
from backend.llm.prompts import COLLECT_PROMPT, GRAPH_QUERY_PROMPT, format_prompt
from backend.llm.factory import create_llm_provider
from backend.tools.graph_query import graph_query
import json


async def collect_info(state: AgentState) -> AgentState:
    """提取症状关键词，通过图谱查询候选病害。"""
    llm = create_llm_provider()

    # 取用户最新消息
    user_msg = ""
    for msg in reversed(state["messages"]):
        if msg.get("role") == "user":
            user_msg = msg.get("content", "")
            break

    # Step 1: 提取症状
    prompt = format_prompt(COLLECT_PROMPT, question=user_msg)
    response = await llm.generate([{"role": "user", "content": prompt}])

    try:
        # 尝试从 LLM 输出中提取 JSON
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(response[start:end])
            extracted = data.get("symptoms", [])
        else:
            extracted = []
    except json.JSONDecodeError:
        extracted = []

    # 累积症状：新提取的 + 已有的
    for s in extracted:
        if s and s not in state["symptoms"]:
            state["symptoms"].append(s)

    # Step 2: 生成 Cypher 查询候选病害
    if state["symptoms"]:
        context = ""
        if state.get("missing_info"):
            context = "已有追问信息: " + ", ".join(state.get("missing_info", []))

        gq_prompt = format_prompt(
            GRAPH_QUERY_PROMPT,
            symptoms=str(state["symptoms"]),
            context=context
        )
        cypher_response = await llm.generate([{"role": "user", "content": gq_prompt}])

        # 清理 Cypher 输出
        cypher = cypher_response.strip()
        if cypher.startswith("```"):
            lines = cypher.split("\n")
            cypher = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        result = graph_query.invoke({"cypher": cypher})

        if not result.get("error"):
            # 解析图谱结果为候选病害
            nodes = result.get("nodes", [])
            for node in nodes:
                if "Disease" in node.get("labels", []):
                    state["candidate_diseases"].append({
                        "name": node["properties"].get("name", ""),
                        "scientific_name": node["properties"].get("scientific_name", ""),
                        "confidence": 0.5,  # 初始置信度，后续由 check_confidence 更新
                        "matched_symptoms": state["symptoms"].copy(),
                    })

    state["node_events"].append({
        "node": "collect_info",
        "status": "complete",
        "data": {
            "symptoms": state["symptoms"],
            "candidates": [d["name"] for d in state["candidate_diseases"]]
        }
    })

    return state
