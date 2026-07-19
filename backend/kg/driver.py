"""共享 Neo4j Driver —— 统一管理连接池，避免重复创建。

用法：
    from backend.kg.driver import get_driver, init_driver, close_driver

    # 应用启动时
    init_driver()

    # 工具中使用
    driver = get_driver()

    # 应用关闭时
    close_driver()
"""
import logging
import threading

from neo4j import GraphDatabase
from backend.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger(__name__)

_driver = None
_lock = threading.Lock()


def init_driver() -> None:
    """初始化 Neo4j driver（应在 lifespan startup 中调用）。"""
    global _driver
    with _lock:
        if _driver is not None:
            return  # 已初始化
        try:
            _driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD),
                max_connection_lifetime=3600,
                max_connection_pool_size=10,
            )
            # 验证连接
            with _driver.session() as session:
                session.run("RETURN 1")
            logger.info("Neo4j driver 初始化成功: %s", NEO4J_URI)
        except Exception:
            logger.warning("Neo4j driver 初始化失败 (图谱查询将不可用): %s", NEO4J_URI,
                           exc_info=True)
            _driver = None


def get_driver():
    """获取共享的 Neo4j driver。返回 None 表示 Neo4j 不可用。"""
    global _driver
    if _driver is None:
        # 自动尝试初始化（兼容未显式调 init_driver 的场景）
        init_driver()
    return _driver


def close_driver() -> None:
    """关闭 driver 并释放连接池（应在 lifespan shutdown 中调用）。"""
    global _driver
    with _lock:
        if _driver is not None:
            _driver.close()
            _driver = None
            logger.info("Neo4j driver 已关闭")


def _is_read_only(cypher: str) -> bool:
    """安全检查：只允许只读 MATCH 语句。

    使用正则匹配代替简单的 startsWith + 换行检测，
    防御通过注释 / 空白符绕过的注入攻击。

    只允许以 MATCH 开头且不含写操作关键字的语句。
    """
    import re

    cypher_normalized = cypher.strip()

    # 必须由 MATCH 开头
    if not re.match(r'^\s*MATCH\b', cypher_normalized, re.IGNORECASE):
        return False

    # 禁止的写操作关键字（使用词边界匹配，防止误杀字段名）
    forbidden_pattern = r'\b(CREATE|DELETE|SET\b|MERGE|REMOVE|DROP|DETACH)\b'

    # 移除注释后再检查
    # 移除单行注释 //
    no_comments = re.sub(r'//[^\n]*', '', cypher_normalized)
    # 移除块注释 /* ... */
    no_comments = re.sub(r'/\*.*?\*/', '', no_comments, flags=re.DOTALL)

    if re.search(forbidden_pattern, no_comments, re.IGNORECASE):
        return False

    return True