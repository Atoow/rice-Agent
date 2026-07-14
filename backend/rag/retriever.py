"""向量检索引擎：文档入库、语义搜索、持久化。

基于 numpy 实现余弦相似度检索，替代 Chroma（避免 C 扩展兼容性问题）。
向量数据持久化到磁盘，重启不丢失。
"""
import os, json
import numpy as np
from backend.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, RETRIEVAL_TOP_K, MIN_RELEVANCE_SCORE
from backend.rag.embedding import OllamaEmbedding


class Retriever:
    """向量检索和知识库管理的统一入口。"""

    def __init__(
        self,
        embedding: OllamaEmbedding,
        persist_dir: str = CHROMA_PERSIST_DIR,
        collection_name: str = CHROMA_COLLECTION_NAME,
    ):
        self.embedding = embedding
        self.persist_dir = persist_dir
        self.collection_name = collection_name

        os.makedirs(persist_dir, exist_ok=True)

        # 加载已有数据
        self._vectors: np.ndarray | None = None   # shape: (N, dim)
        self._documents: list[str] = []
        self._sources: list[str] = []
        self._indices: list[int] = []
        self._load()

    # === 持久化 ===

    def _vectors_path(self):
        return os.path.join(self.persist_dir, f"{self.collection_name}_vectors.npy")

    def _meta_path(self):
        return os.path.join(self.persist_dir, f"{self.collection_name}_meta.json")

    def _save(self):
        if self._vectors is not None and len(self._vectors) > 0:
            np.save(self._vectors_path(), self._vectors)
        meta = {
            "documents": self._documents,
            "sources": self._sources,
            "indices": self._indices,
        }
        with open(self._meta_path(), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)

    def _load(self):
        vpath = self._vectors_path()
        mpath = self._meta_path()
        if os.path.exists(vpath) and os.path.exists(mpath):
            self._vectors = np.load(vpath)
            with open(mpath, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self._documents = meta["documents"]
            self._sources = meta["sources"]
            self._indices = meta["indices"]

    # === 文档入库 ===

    def _remove_by_source(self, source: str) -> int:
        """删除指定来源文件的所有向量条目，返回删除数量。"""
        if self._vectors is None or len(self._vectors) == 0:
            return 0

        keep_mask = [s != source for s in self._sources]
        removed = len(self._vectors) - sum(keep_mask)
        if removed == 0:
            return 0

        self._vectors = self._vectors[keep_mask]
        self._documents = [d for d, keep in zip(self._documents, keep_mask) if keep]
        self._sources = [s for s, keep in zip(self._sources, keep_mask) if keep]
        self._indices = [i for i, keep in zip(self._indices, keep_mask) if keep]
        self._save()
        return removed


    def add_documents(self, chunks: list[dict]) -> int:
        """将文档块向量化并存入本地。重复上传同一文件会先清理旧数据。

        Args:
            chunks: [{"content": "文本", "source": "文件名", "index": 0}, ...]

        Returns:
            入库的文本块数量
        """
        if not chunks:
            return 0

        # 去重：先删除同一来源的旧条目
        sources_seen = set()
        for chunk in chunks:
            src = chunk.get("source", "")
            if src and src not in sources_seen:
                sources_seen.add(src)
                removed = self._remove_by_source(src)
                if removed:
                    print(f"已清理旧数据: {src} ({removed} 条)")

        texts = [chunk["content"] for chunk in chunks]
        new_vectors = np.array(self.embedding.embed_batch(texts), dtype=np.float32)

        if self._vectors is None or len(self._vectors) == 0:
            self._vectors = new_vectors
        else:
            self._vectors = np.vstack([self._vectors, new_vectors])

        for chunk in chunks:
            self._documents.append(chunk["content"])
            self._sources.append(chunk["source"])
            self._indices.append(chunk["index"])

        self._save()
        return len(chunks)

    # === 语义检索 ===

    def search(self, query: str, top_k: int = RETRIEVAL_TOP_K, min_score: float = MIN_RELEVANCE_SCORE) -> list[dict]:
        """语义检索：输入问题，返回最相关的文档片段。

        Returns:
            [{"content": "文本", "source": "文件名", "relevance": 0.92}, ...]
            只返回相关度 >= min_score 的结果
        """
        if self._vectors is None or len(self._vectors) == 0:
            return []

        # 查询向量化
        q_embed = np.array(self.embedding.embed(query), dtype=np.float32)

        # 余弦相似度计算
        q_norm = q_embed / (np.linalg.norm(q_embed) + 1e-8)
        v_norms = self._vectors / (np.linalg.norm(self._vectors, axis=1, keepdims=True) + 1e-8)
        similarities = np.dot(v_norms, q_norm)

        # Top-K（先取更多候选再按阈值过滤）
        k = min(top_k * 2, len(similarities))  # 多取一些候选
        top_indices = np.argpartition(similarities, -k)[-k:]
        top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]

        formatted = []
        for idx in top_indices:
            sim = float(similarities[idx])
            if sim < min_score:
                continue  # 跳过低相关度结果
            formatted.append({
                "content": self._documents[idx],
                "source": self._sources[idx],
                "relevance": round(max(0, sim), 4),
            })
            if len(formatted) >= top_k:
                break

        return formatted

    # === 统计 ===

    def get_collection_stats(self) -> dict:
        count = len(self._documents)
        dim = self._vectors.shape[1] if self._vectors is not None and len(self._vectors) > 0 else 0
        unique_sources = sorted(set(self._sources)) if self._sources else []
        return {
            "total_chunks": count,
            "collection_name": self.collection_name,
            "vector_dim": dim,
            "document_files": unique_sources,
        }
