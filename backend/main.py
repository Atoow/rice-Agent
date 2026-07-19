"""FastAPI 主入口 —— 启动 Agent 服务。"""
import logging
import os
import sys
import traceback
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from backend.config import DATABASE_URL
from backend.rag.embedding import OllamaEmbedding
from backend.rag.retriever import Retriever
from backend.db.models import init_db
from backend.routes.chat import router as chat_router
from backend.routes.admin import router as admin_router

# ── 日志配置 ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# === 生命周期管理 ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化依赖，关闭时清理资源。

    所有可能失败的初始化都放在此处，避免 import 阶段崩溃。
    即使部分组件初始化失败，app 对象仍可创建，health check 仍可响应。
    """
    # ── startup ──

    # 1. 向量检索引擎
    logger.info("正在初始化向量检索引擎...")
    embedding = None
    retriever = None
    try:
        embedding = OllamaEmbedding()
        retriever = Retriever(embedding=embedding)
        stats = retriever.get_collection_stats()
        logger.info("向量库已加载: %d 个片段", stats["total_chunks"])
    except Exception:
        logger.warning("向量检索引擎初始化失败（文档检索将不可用）:", exc_info=True)

    # 2. Neo4j 图谱
    from backend.kg.driver import init_driver
    init_driver()

    # 3. 注入共享 Retriever 到 vector_search 工具
    #    确保 admin 上传后 agent 检索能感知新数据
    if retriever is not None:
        from backend.tools.vector_search import set_retriever
        set_retriever(retriever)

    # 文档上传目录
    doc_dir = os.path.join(os.path.dirname(__file__), "..", "data", "documents")
    os.makedirs(doc_dir, exist_ok=True)

    app.state.retriever = retriever
    app.state.doc_dir = doc_dir

    # 4. 数据库
    try:
        init_db()
        logger.info("SQLite 数据库初始化完成: %s", DATABASE_URL)
    except Exception:
        logger.warning("数据库初始化失败:", exc_info=True)

    logger.info("应用启动完成")

    # ── yield: 应用运行中 ──
    yield

    # ── shutdown ──
    logger.info("应用关闭中...")
    from backend.kg.driver import close_driver
    close_driver()
    logger.info("清理完成")


# === 应用创建 ===

app = FastAPI(
    title="水稻种植智能 Agent",
    description="基于 LangGraph 的多步推理水稻病虫害诊断系统",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # 生产环境应改为具体域名
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "水稻 Agent 运行中", "version": "2.0.0"}


@app.get("/admin", include_in_schema=False)
async def admin_redirect():
    return RedirectResponse(url="/admin.html")


# === 路由 ===
app.include_router(chat_router)
app.include_router(admin_router)

# === 静态文件 (必须放在路由之后，否则覆盖 API) ===
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    logger.info("前端页面已挂载: %s", FRONTEND_DIR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
