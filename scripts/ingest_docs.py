"""文档摄入脚本 —— 将 data/documents/ 下的 PDF/MD/TXT 向量化入库。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.rag.loader import DocumentLoader
from backend.rag.embedding import OllamaEmbedding
from backend.rag.retriever import Retriever

if __name__ == "__main__":
    doc_dir = os.path.join(os.path.dirname(__file__), "..", "data", "documents")
    doc_dir = os.path.abspath(doc_dir)

    if not os.path.exists(doc_dir):
        print(f"文档目录不存在: {doc_dir}")
        exit(1)

    files = [f for f in os.listdir(doc_dir)
             if f.endswith((".pdf", ".md", ".txt"))]
    if not files:
        print(f"文档目录为空: {doc_dir}")
        exit(1)

    print(f"=== 开始向量化 {len(files)} 个文档 ===")
    for f in files:
        print(f"  - {f}")

    loader = DocumentLoader()
    chunks = loader.load_directory(doc_dir)
    print(f"\n共切分 {len(chunks)} 个文本块")

    embedding = OllamaEmbedding()
    retriever = Retriever(embedding=embedding)
    count = retriever.add_documents(chunks)

    stats = retriever.get_collection_stats()
    print(f"\n=== 完成！向量库已入库 {count} 个片段 ===")
    print(f"统计: {stats}")
