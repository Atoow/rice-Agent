"""FastAPI 主入口 —— 启动 Agent 服务。"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.config import DATABASE_URL
from backend.rag.embedding import OllamaEmbedding
from backend.rag.retriever import Retriever
from backend.db.models import init_db
from backend.routes.chat import router as chat_router
from backend.routes.admin import init_admin, router as admin_router

# === 应用创建 ===
app = FastAPI(
    title="水稻种植智能 Agent",
    description="基于 LangGraph 的多步推理水稻病虫害诊断系统",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "水稻 Agent 运行中", "version": "2.0.0"}


# === 依赖初始化 ===
print("正在初始化向量检索引擎...")
embedding = OllamaEmbedding()
retriever = Retriever(embedding=embedding)
print(f"向量库已加载: {retriever.get_collection_stats()['total_chunks']} 个片段")

# 文档上传目录
doc_dir = os.path.join(os.path.dirname(__file__), "..", "data", "documents")
os.makedirs(doc_dir, exist_ok=True)

# 注入
init_admin(retriever, doc_dir)
init_db()
print(f"SQLite 数据库初始化完成: {DATABASE_URL}")

# === 路由 ===
app.include_router(chat_router)
app.include_router(admin_router)

# === 静态文件 ===
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    print(f"前端页面已挂载: {FRONTEND_DIR}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
