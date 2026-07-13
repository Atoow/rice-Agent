"""置信度判断节点 —— 评估诊断完整性，决定追问还是继续。"""
from backend.agent.state import AgentState
from backend.llm.prompts import CHECK_CONFIDENCE_PROMPT, format_prompt
from backend.llm.factory import create_llm_provider
import json


async def check_confidence(state: AgentState) -> AgentState:
    """判断当前信息是否足够确诊。

    置信度 >= 0.7: 进入验证流程
    置信度 < 0.7 且追问 < 3 轮: 生成追问
    置信度 < 0.7 且追问 >= 3 轮: 降级输出
    """
    llm = create_llm_provider()

    candidates_str = json.dumps(state["candidate_diseases"][:5], ensure_ascii=False)
    prompt = format_prompt(
        CHECK_CONFIDENCE_PROMPT,
        symptoms=str(state["symptoms"]),
        candidates=candidates_str,
        clarify_count=str(state["clarify_count"])
    )

    response = await llm.generate([{"role": "user", "content": prompt}])

    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(response[start:end])
            state["confidence"] = data.get("confidence", 0.5)
            state["missing_info"] = data.get("missing_info", [])
        else:
            state["confidence"] = 0.5
    except json.JSONDecodeError:
        state["confidence"] = state.get("confidence", 0.5)

    state["node_events"].append({
        "node": "check_confidence",
        "status": "complete",
        "data": {
            "confidence": state["confidence"],
            "missing": state["missing_info"],
            "rounds": state["clarify_count"]
        }
    })

    return state
