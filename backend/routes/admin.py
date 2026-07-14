"""管理后台路由 —— 文档上传 + 统计查询。"""
import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse
from backend.rag.loader import DocumentLoader
from backend.rag.retriever import Retriever

router = APIRouter(prefix="/admin", tags=["管理"])

# 延迟初始化
_retriever: Retriever | None = None
UPLOAD_DIR: str = ""


def init_admin(retriever: Retriever, upload_dir: str):
    global _retriever, UPLOAD_DIR
    _retriever = retriever
    UPLOAD_DIR = upload_dir


@router.get("/", include_in_schema=False)
@router.get("", include_in_schema=False)
async def admin_page():
    return RedirectResponse(url="/admin.html")


@router.get("/stats")
async def get_stats():
    if _retriever is None:
        raise HTTPException(500, "服务未初始化")
    stats = _retriever.get_collection_stats()
    return stats


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if _retriever is None:
        raise HTTPException(500, "服务未初始化")

    # 保存文件
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # 处理文档
    loader = DocumentLoader()
    chunks = loader.load_file(file_path)

    # 入库
    count = _retriever.add_documents(chunks)

    return {"filename": file.filename, "chunks": count, "status": "ok"}
