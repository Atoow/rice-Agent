"""图谱查询工具 —— 执行只读 Cypher 查询，查询 Neo4j 水稻知识图谱。"""
from langchain_core.tools import tool
from backend.kg.driver import get_driver, _is_read_only


@tool
def graph_query(cypher: str) -> dict:
    """执行只读 Cypher 查询，查询水稻知识图谱。

    安全限制：仅允许 MATCH 开头的只读语句。
    图谱包含实体：Disease(病害), Symptom(症状), Control(防治措施),
    Variety(品种), EnvCondition(环境条件), GrowthStage(生育期)

    常用查询模式：
    - 症状查病害: MATCH (s:Symptom)-[r:INDICATES]->(d:Disease) WHERE s.name IN [...]
    - 病害画像: MATCH (d:Disease {name: '稻瘟病'})-[r]-(n) RETURN d, type(r), r, n
    - 品种抗性: MATCH (v:Variety {name: '...'})-[r:RESISTANT_TO|SUSCEPTIBLE_TO]->(d)

    Args:
        cypher: Cypher 查询语句

    Returns:
        {nodes: [...], relationships: [...], error: str|None}
    """
    if not _is_read_only(cypher):
        return {"nodes": [], "relationships": [], "error": "安全限制：仅允许 MATCH 只读查询"}

    driver = get_driver()
    if driver is None:
        return {"nodes": [], "relationships": [], "error": "Neo4j 未连接"}

    try:
        with driver.session() as session:
            result = session.run(cypher)
            records = list(result)

            nodes = []
            relationships = []
            seen_nodes = set()
            seen_rels = set()

            for record in records:
                for value in record.values():
                    if hasattr(value, "labels") and hasattr(value, "id"):
                        node_id = value.id
                        if node_id not in seen_nodes:
                            seen_nodes.add(node_id)
                            nodes.append({
                                "id": node_id,
                                "labels": list(value.labels),
                                "properties": dict(value.items()),
                            })
                    elif hasattr(value, "type") and hasattr(value, "id"):
                        rel_id = value.id
                        if rel_id not in seen_rels:
                            seen_rels.add(rel_id)
                            relationships.append({
                                "id": rel_id,
                                "type": value.type,
                                "start_node": value.start_node.id,
                                "end_node": value.end_node.id,
                                "properties": dict(value.items()),
                            })

        return {"nodes": nodes, "relationships": relationships, "error": None}

    except Exception as e:
        return {"nodes": [], "relationships": [], "error": str(e)}
