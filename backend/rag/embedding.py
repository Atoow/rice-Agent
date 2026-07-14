"""使用 Ollama 的 dmeta-embedding-zh 做中文文本向量化。"""
import ollama
from backend.config import OLLAMA_HOST, EMBED_MODEL


class OllamaEmbedding:
    """封装 Ollama embedding API，支持单条和批量向量化。"""

    def __init__(self, host: str = OLLAMA_HOST, model: str = EMBED_MODEL):
        self.client = ollama.Client(host=host)
        self.model = model

    def embed(self, text: str) -> list[float]:
        """将单段文本转为向量。"""
        response = self.client.embed(model=self.model, input=text)
        return response["embeddings"][0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量将多段文本转为向量。自动分批避免 Ollama tokenize 服务限制。"""
        batch_size = 50
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.client.embed(model=self.model, input=batch)
            all_embeddings.extend(response["embeddings"])
        return all_embeddings
