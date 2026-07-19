"""方案生成节点 & 知识回答节点 —— Agent 推理链的最终输出。"""
from backend.agent.state import AgentState
from backend.llm.prompts import GENERATE_PLAN_PROMPT, KNOWLEDGE_ANSWER_PROMPT, SYSTEM_PROMPT, format_prompt
from backend.llm.factory import create_llm_provider
from backend.tools.vector_search import vector_search
from backend.tools.graph_query import graph_query
import json


async def generate_plan(state: AgentState) -> AgentState:
    """生成最终诊断方案——组合向量检索 + 图谱上下文 + LLM 生成。"""

    # Step 1: 向量检索防治方案
    diagnosis = state.get("final_diagnosis", {})
    disease_name = diagnosis.get("disease", "")
    search_query = f"{disease_name} 防治方法 农药 管理措施"
    docs = vector_search.invoke({"query": search_query, "top_k": 3})

    # Step 2: 图谱查询——获取病害完整画像（症状、防治、环境触发）
    # ⚠ 安全注意：disease_name 直接拼入 Cypher 存在注入风险。
    # 若启用此节点，需先在 graph_query 工具中添加参数化查询支持，
    # 或使用 Neo4j 参数绑定: session.run(cypher, {"disease_name": disease_name})
    graph_context = ""
    if disease_name:
        cypher = f"""
        MATCH (d:Disease)-[r]-(n)
        WHERE d.name = '{disease_name}'
        RETURN d, type(r) as rel_type, r, labels(n) as node_labels, n
        """
        g_result = graph_query.invoke({"cypher": cypher})
        if not g_result.get("error"):
            graph_context = json.dumps(g_result, ensure_ascii=False, indent=2)[:2000]

    # Step 3: 构建 prompt
    docs_text = "\n\n".join([
        f"【来源：{d['source']}，相关度：{d['relevance']}】\n{d['content']}"
        for d in docs
    ])

    # 验证状态文本
    vr = state.get("verification_result", {})
    verification_status = f"{'✅ 通过' if vr.get('valid') else '⚠️ 未完全通过，诊断存在不确定性'}"

    prompt = format_prompt(
        GENERATE_PLAN_PROMPT,
        diagnosis=json.dumps(diagnosis, ensure_ascii=False),
        verification_status=verification_status,
        documents=docs_text
    )

    # Step 4: LLM 生成方案
    llm = create_llm_provider()
    plan = await llm.generate([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])

    # 组装完整回答（不含来源引用，来源由前端单独展示）
    full_answer = plan

    state["messages"].append({
        "role": "assistant",
        "content": full_answer,
        "node_type": "generate_plan"
    })

    state["sources"] = [{"content": d["content"], "source": d["source"],
                         "relevance": d["relevance"], "type": "vector"} for d in docs]
    if graph_context:
        state["sources"].append({"content": "知识图谱查询结果", "source": "Neo4j Rice KG",
                                 "relevance": 1.0, "type": "graph"})

    state["node_events"].append({
        "node": "generate_plan",
        "status": "complete",
        "data": {"answer_length": len(plan), "sources_count": len(state["sources"])}
    })

    return state


async def knowledge_answer(state: AgentState) -> AgentState:
    """知识类问题——直接向量检索 + LLM 回答，不走诊断链路。"""
    llm = create_llm_provider()

    user_msg = ""
    for msg in reversed(state["messages"]):
        if msg.get("role") == "user":
            user_msg = msg.get("content", "")
            break

    # 检索
    docs = vector_search.invoke({"query": user_msg, "top_k": 3})

    if not docs:
        state["messages"].append({
            "role": "assistant",
            "content": "知识库中暂无相关信息，建议您咨询当地农技站或拨打12316农业服务热线。",
            "node_type": "knowledge_answer"
        })
        return state

    docs_text = "\n\n".join([
        f"【{d['source']}】\n{d['content']}" for d in docs
    ])

    prompt = format_prompt(KNOWLEDGE_ANSWER_PROMPT, context=docs_text, question=user_msg)
    answer = await llm.generate([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])

    state["messages"].append({
        "role": "assistant",
        "content": answer,
        "node_type": "knowledge_answer"
    })

    state["sources"] = [{"content": d["content"], "source": d["source"],
                         "relevance": d["relevance"], "type": "vector"} for d in docs]

    state["node_events"].append({
        "node": "knowledge_answer",
        "status": "complete",
        "data": {"sources_count": len(docs)}
    })

    return state
