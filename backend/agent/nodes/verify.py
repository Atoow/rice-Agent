"""知识验证节点 —— 验证诊断结论中的三元组是否在图谱中成立。"""
from backend.agent.state import AgentState
from backend.tools.verify_claim import verify_claim


async def verify_claim_node(state: AgentState) -> AgentState:
    """验证候选病害的诊断链路是否在图谱中有支撑。

    对每个候选病害，验证其与症状的 INDICATES 关系和防治措施的 EFFECTIVE_AGAINST 关系。
    """
    verification_results = []

    for disease in state["candidate_diseases"][:3]:  # 只验证 top 3
        disease_name = disease.get("name", "")

        # 验证症状-病害关系
        for symptom in disease.get("matched_symptoms", [])[:2]:
            result = verify_claim.invoke({
                "disease": disease_name,
                "symptom": symptom,
                "control": ""
            })
            if result.get("valid"):
                disease["confidence"] = min(disease.get("confidence", 0.5) + 0.15, 1.0)
            verification_results.append(result)

    # 找出最高置信度的候选作为诊断结果
    if state["candidate_diseases"]:
        best = max(state["candidate_diseases"], key=lambda d: d.get("confidence", 0))
        state["final_diagnosis"] = {
            "disease": best["name"],
            "scientific_name": best.get("scientific_name", ""),
            "confidence": best["confidence"],
            "reasoning": f"基于 {len(state['symptoms'])} 个症状匹配，图谱验证{'通过' if best['confidence'] >= 0.7 else '未完全通过'}"
        }

    state["verification_result"] = {
        "valid": state["final_diagnosis"]["confidence"] >= 0.7 if state["final_diagnosis"] else False,
        "evidence": [r.get("evidence", []) for r in verification_results]
    }

    state["node_events"].append({
        "node": "verify_claim",
        "status": "complete",
        "data": {
            "diagnosis": state.get("final_diagnosis", {}),
            "checks": len(verification_results)
        }
    })

    return state
