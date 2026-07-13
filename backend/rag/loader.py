"""文档加载器：支持 PDF/MD/TXT，自动切分文本块。"""
import os
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.config import CHUNK_SIZE, CHUNK_OVERLAP


class DocumentLoader:
    """统一文档加载入口：自动识别文件类型，加载后切分。"""

    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", ".", "；", ";", " ", ""],
        )

    def load_file(self, file_path: str) -> list[dict]:
        """加载单个文件，返回切分后的文本块列表。

        Returns:
            [{"content": "文本块", "source": "文件名", "index": 0}, ...]
        """
        ext = Path(file_path).suffix.lower()
        source_name = os.path.basename(file_path)

        if ext == ".pdf":
            text = self._read_pdf(file_path)
        elif ext in (".txt", ".md"):
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            raise ValueError(f"不支持的文件类型: {ext}。支持: .pdf, .md, .txt")

        # langchain_text_splitters 的 split_text 直接接收字符串
        chunk_texts = self.splitter.split_text(text)

        return [
            {"content": chunk, "source": source_name, "index": i}
            for i, chunk in enumerate(chunk_texts)
        ]

    def _read_pdf(self, file_path: str) -> str:
        """用 pypdf 提取 PDF 文本。"""
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)

    def load_directory(self, dir_path: str) -> list[dict]:
        """加载整个目录下的所有支持文件。"""
        all_chunks = []
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            if os.path.isfile(file_path):
                ext = Path(file_path).suffix.lower()
                if ext in (".pdf", ".md", ".txt"):
                    chunks = self.load_file(file_path)
                    all_chunks.extend(chunks)
                    print(f"已加载 {filename}: {len(chunks)} 个文本块")
        return all_chunks
