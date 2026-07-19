"""LLM 工厂函数：根据配置创建对应的 Provider 实例。"""
import logging

from backend.config import (
    LLM_PROVIDER, OLLAMA_HOST, LLM_MODEL,
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL,
)
from backend.llm.provider import LLMProvider, OllamaProvider, DeepSeekProvider

logger = logging.getLogger(__name__)


def create_llm_provider() -> LLMProvider:
    """根据 LLM_PROVIDER 配置创建对应的 Provider。

    Returns:
        OllamaProvider 或 DeepSeekProvider 实例
    """
    provider_name = LLM_PROVIDER.lower()

    if provider_name == "deepseek":
        if not DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY 未设置，无法使用 DeepSeek")
        logger.info("使用 DeepSeek API (%s)", DEEPSEEK_BASE_URL)
        return DeepSeekProvider(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

    # 默认：Ollama
    logger.info("使用 Ollama (%s, %s)", OLLAMA_HOST, LLM_MODEL)
    return OllamaProvider(host=OLLAMA_HOST, model=LLM_MODEL)
