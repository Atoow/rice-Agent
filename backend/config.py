"""集中管理所有配置项。"""
import os

# === LLM 配置 ===
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # ollama | deepseek
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "shaw/dmeta-embedding-zh")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# === Neo4j 配置 ===
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "rice-agent-2026")

# === 向量检索配置（保留） ===
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")
CHROMA_COLLECTION_NAME = "rice_knowledge"
RETRIEVAL_TOP_K = 3
MIN_RELEVANCE_SCORE = 0.35

# === 文档处理配置 ===
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# === 数据库配置 ===
DATABASE_URL = os.path.join(os.path.dirname(__file__), "..", "rice-agent.db")

# === Agent 配置 ===
MAX_CLARIFY_ROUNDS = 3        # 最多追问轮数
CONFIDENCE_THRESHOLD = 0.7    # 诊断置信度阈值
MAX_HISTORY_TURNS = 10        # 对话历史保留轮数
