"""向量检索工具 —— 包装为 LangChain Tool。

通过 set_retriever() 注入与 admin 模块共享的 Retriever 实例，
确保文档上传后 agent 检索能感知新数据。
"""
from langchain_core.tools import tool
from backend.rag.embedding import OllamaEmbedding
from backend.rag.retriever import Retriever
from backend.config import RETRIEVAL_TOP_K

# 模块级单例（优先使用外部注入的实例）
_retriever: Retriever | None = None


def set_retriever(retriever: Retriever) -> None:
    """注入共享 Retriever 实例（由 lifespan 调用）。"""
    global _retriever
    _retriever = retriever


def get_retriever() -> Retriever:
    """获取 Retriever 实例（优先返回注入的，否则自建）。"""
    global _retriever
    if _retriever is None:
        embedding = OllamaEmbedding()
        _retriever = Retriever(embedding=embedding)
    return _retriever


@tool
def vector_search(query: str, top_k: int = RETRIEVAL_TOP_K) -> list[dict]:
    """在知识库文档中语义检索相关内容。

    当需要查找水稻种植技术、病虫害防治方法、品种特性等
    文档中的信息时使用此工具。

    Args:
        query: 搜索查询文本
        top_k: 返回结果数量，默认 3

    Returns:
        [{content, source, relevance}] — 相关文档片段列表
    """
    retriever = get_retriever()
    results = retriever.search(query, top_k=top_k)
    return [
        {"content": r["content"], "source": r["source"], "relevance": r["relevance"]}
        for r in results
    ]
