"""向量检索工具 —— 复用现有 Retriever，包装为 LangChain Tool。"""
from langchain_core.tools import tool
from backend.rag.embedding import OllamaEmbedding
from backend.rag.retriever import Retriever
from backend.config import RETRIEVAL_TOP_K, MIN_RELEVANCE_SCORE

# 模块级单例
_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    """获取或初始化全局 Retriever 实例。"""
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
    # 不截断内容，让 LLM 看到完整上下文
    return [
        {"content": r["content"], "source": r["source"], "relevance": r["relevance"]}
        for r in results
    ]
