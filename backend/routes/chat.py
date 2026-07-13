"""对话路由 —— SSE 流式推送 Agent 推理过程，支持 interrupt/resume 追问机制。"""
import json
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel, Field

from backend.agent.graph import get_graph
from backend.agent.state import initial_state

router = APIRouter(prefix="/chat", tags=["对话"])


class ChatRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    question: str = Field(..., min_length=1, max_length=500)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[dict]
    reasoning_trace: list[dict]


# ── helpers ──────────────────────────────────────────────


def _as_dict(msg) -> dict:
    """兼容 dict 和 LangChain Message 对象（HumanMessage / AIMessage）。"""
    if hasattr(msg, "content"):
        return {
            "role": getattr(msg, "type", "unknown"),
            "content": msg.content,
            "node_type": (getattr(msg, "response_metadata", {}) or {}).get("node_type", ""),
        }
    return msg


def _extract_clarify(messages: list) -> str:
    """从 messages 列表中提取最后一轮 clarify 追问文本。"""
    for msg in reversed(messages):
        d = _as_dict(msg)
        if d.get("node_type") == "clarify":
            return d.get("content", "")
    return ""


def _extract_final_answer(messages: list) -> str:
    """从 messages 列表中提取最终答案。"""
    for msg in reversed(messages):
        d = _as_dict(msg)
        if d.get("node_type") in ("generate_plan", "knowledge_answer"):
            return d.get("content", "")
    return ""


# ── SSE stream endpoint ──────────────────────────────────


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    """SSE 流式接口 —— 实时推送推理过程。

    首次调用：创建新状态图，逐节点推送推理事件。
    追问调用：同一 session_id 下，从上次 interrupt() 断点
              恢复执行，将新输入传给 clarify 节点。

    事件类型：
      - node_event : 节点状态  {node, status, data}
      - clarify    : 追问文本  {type, content}
      - answer     : 最终回答  {type, content}
      - sources    : 引用来源  {type, content}
      - error      : 错误      {type, content}
    """
    graph = get_graph()
    config = {"configurable": {"thread_id": req.session_id}}

    async def _generate():
        try:
            # ── 判断是首次还是恢复 ──
            snapshot = await graph.aget_state(config)
            is_resuming = bool(snapshot and snapshot.next)

            final_state = None

            if is_resuming:
                resume_data = {"role": "user", "content": req.question}
                async for event in graph.astream(Command(resume=resume_data), config):
                    for node_name, node_output in event.items():
                        for line in _yield_events(node_output):
                            yield line
                        if node_name == "clarify":
                            q = _extract_clarify(node_output.get("messages", []))
                            if q:
                                yield _sse({"type": "clarify", "content": q})
                        final_state = node_output
            else:
                state = initial_state()
                state["messages"].append({"role": "user", "content": req.question})
                async for event in graph.astream(state, config):
                    for node_name, node_output in event.items():
                        for line in _yield_events(node_output):
                            yield line
                        if node_name == "clarify":
                            q = _extract_clarify(node_output.get("messages", []))
                            if q:
                                yield _sse({"type": "clarify", "content": q})
                        final_state = node_output

            # ── 最终结果 ──
            if final_state:
                answer = _extract_final_answer(final_state.get("messages", []))
                if answer:
                    yield _sse({"type": "answer", "content": answer})
                sources = final_state.get("sources", [])
                if sources:
                    yield _sse({"type": "sources", "content": sources})

            yield "data: [DONE]\n\n"

        except Exception as exc:
            import traceback
            traceback.print_exc()
            yield _sse({"type": "error", "content": str(exc)})

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── sync endpoint (debug / non-SSE) ──────────────────────


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """非流式接口 —— 同步返回完整结果。"""
    graph = get_graph()

    # 尝试恢复
    config = {"configurable": {"thread_id": req.session_id}}
    snapshot = await graph.aget_state(config)
    is_resuming = bool(snapshot and snapshot.next)

    if is_resuming:
        final_state = await graph.ainvoke(Command(resume={"role": "user", "content": req.question}), config)
    else:
        state = initial_state()
        state["messages"].append({"role": "user", "content": req.question})
        final_state = await graph.ainvoke(state, config)

    answer = _extract_final_answer(final_state.get("messages", []))
    if not answer:
        answer = _extract_clarify(final_state.get("messages", []))

    return ChatResponse(
        session_id=req.session_id,
        answer=answer,
        sources=final_state.get("sources", []),
        reasoning_trace=final_state.get("node_events", []),
    )


# ── inline helpers ───────────────────────────────────────


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _yield_events(node_output: dict) -> list[str]:
    """收集 node_events 的 SSE 行，返回列表供调用方 yield。"""
    lines = []
    if "node_events" in node_output:
        for evt in node_output["node_events"]:
            lines.append(_sse({"type": "node_event", **evt}))
    return lines
