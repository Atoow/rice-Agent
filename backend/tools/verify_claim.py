"""知识验证工具 —— 验证 LLM 输出的病害-症状-防治三元组是否在图谱中成立。"""
from langchain_core.tools import tool
from backend.kg.driver import get_driver


@tool
def verify_claim(disease: str, symptom: str = "", control: str = "") -> dict:
    """验证一个病害-症状-防治关联是否在图谱中有支撑。

    Args:
        disease: 病害名称，如 "稻瘟病"
        symptom: 症状描述（可选），如 "叶片褐色斑点"
        control: 防治措施（可选），如 "三环唑"

    Returns:
        {valid: bool, evidence: [{source_type, match, path}]}
    """
    driver = get_driver()
    if driver is None:
        return {"valid": False, "evidence": [{
            "source_type": "graph",
            "match": "driver_unavailable",
            "path": "Neo4j 未连接"
        }]}

    evidence = []
    all_valid = True

    with driver.session() as session:

        # 验证 1: 病害是否存在
        result = session.run(
            "MATCH (d:Disease) WHERE d.name CONTAINS $name RETURN d.name",
            name=disease
        )
        disease_records = list(result)
        if disease_records:
            evidence.append({
                "source_type": "graph",
                "match": "disease_exists",
                "path": f"Disease(name={disease_records[0]['d.name']})"
            })
        else:
            all_valid = False
            evidence.append({
                "source_type": "graph",
                "match": "disease_not_found",
                "path": f"No Disease matching '{disease}'"
            })

        # 验证 2: 症状-病害关系
        if symptom and disease_records:
            result = session.run(
                """MATCH (s:Symptom)-[r:INDICATES]->(d:Disease)
                   WHERE s.name CONTAINS $symptom AND d.name CONTAINS $disease
                   RETURN s.name, d.name, r.weight""",
                symptom=symptom, disease=disease
            )
            sym_records = list(result)
            if sym_records:
                evidence.append({
                    "source_type": "graph",
                    "match": "symptom_disease_link",
                    "path": f"Symptom({sym_records[0]['s.name']}) -> "
                            f"Disease({sym_records[0]['d.name']}) "
                            f"weight={sym_records[0]['r.weight']}"
                })
            else:
                all_valid = False
                evidence.append({
                    "source_type": "graph",
                    "match": "symptom_link_not_found",
                    "path": f"No INDICATES path: '{symptom}' -> '{disease}'"
                })

        # 验证 3: 防治-病害关系
        if control and disease_records:
            result = session.run(
                """MATCH (c:Control)-[r:EFFECTIVE_AGAINST]->(d:Disease)
                   WHERE c.name CONTAINS $control AND d.name CONTAINS $disease
                   RETURN c.name, d.name""",
                control=control, disease=disease
            )
            ctrl_records = list(result)
            if ctrl_records:
                evidence.append({
                    "source_type": "graph",
                    "match": "control_disease_link",
                    "path": f"Control({ctrl_records[0]['c.name']}) -> "
                            f"Disease({ctrl_records[0]['d.name']})"
                })
            else:
                all_valid = False
                evidence.append({
                    "source_type": "graph",
                    "match": "control_link_not_found",
                    "path": f"No EFFECTIVE_AGAINST path: '{control}' -> '{disease}'"
                })

    return {
        "valid": all_valid,
        "evidence": evidence
    }
