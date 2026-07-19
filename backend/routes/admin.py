"""管理后台路由 —— 文档上传 + 统计查询。

依赖通过 lifespan 注入到 app.state，路由通过 Request.app.state 访问。
"""
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import RedirectResponse
from backend.rag.loader import DocumentLoader
from backend.rag.retriever import Retriever

router = APIRouter(prefix="/admin", tags=["管理"])

# 上传限制
MAX_UPLOAD_SIZE = 50 * 1024 * 1024    # 50 MB
ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt"}


def _get_retriever(request: Request) -> Retriever:
    """从 app.state 获取 retriever，若未初始化则抛出 503。"""
    retriever = request.app.state.retriever
    if retriever is None:
        raise HTTPException(503, "向量检索引擎未就绪，请稍后重试")
    return retriever


def _validate_filename(filename: str) -> str:
    """校验文件名，防御路径穿越攻击。

    返回安全的文件名（仅保留基本名称）。
    """
    # 去除路径分隔符，取纯文件名
    safe_name = os.path.basename(filename)
    if not safe_name or safe_name in (".", ".."):
        raise HTTPException(400, "无效的文件名")
    # 检查扩展名
    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400,
                            f"不支持的文件类型: {ext}。支持: {', '.join(ALLOWED_EXTENSIONS)}")
    return safe_name


@router.get("/", include_in_schema=False)
@router.get("", include_in_schema=False)
async def admin_page():
    return RedirectResponse(url="/admin.html")


@router.get("/stats")
async def get_stats(request: Request):
    retriever = _get_retriever(request)
    return retriever.get_collection_stats()


@router.post("/upload")
async def upload_document(request: Request, file: UploadFile = File(...)):
    retriever = _get_retriever(request)
    doc_dir = request.app.state.doc_dir or ""

    # 校验文件名（防御路径穿越 + 非法扩展名）
    safe_name = _validate_filename(file.filename)

    # 限制文件大小：流式读取，超过上限立即拒绝
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(413, f"文件过大（最大 {MAX_UPLOAD_SIZE // 1024 // 1024} MB）")

    # 保存到安全路径
    file_path = os.path.join(doc_dir, safe_name)
    with open(file_path, "wb") as f:
        f.write(content)

    # 处理文档
    try:
        loader = DocumentLoader()
        chunks = loader.load_file(file_path)
    except ValueError as e:
        os.remove(file_path)  # 清理无效文件
        raise HTTPException(400, str(e))

    # 入库
    count = retriever.add_documents(chunks)

    return {"filename": safe_name, "chunks": count, "status": "ok"}
