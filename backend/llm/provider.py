"""LLM 抽象层：定义统一接口，后续可切换 Ollama / DeepSeek / 通义千问。"""
import logging
from abc import ABC, abstractmethod

import ollama
from backend.config import OLLAMA_HOST, LLM_MODEL

logger = logging.getLogger(__name__)

# 最大重试次数
MAX_RETRIES = 2
# Ollama / DeepSeek 请求超时（秒）
REQUEST_TIMEOUT = 120.0


class LLMProvider(ABC):
    """所有 LLM 后端的抽象基类。"""

    @abstractmethod
    async def generate(self, messages: list[dict]) -> str:
        """接收 messages（OpenAI 格式），返回生成的文本。"""
        ...


class OllamaProvider(LLMProvider):
    """Ollama 本地模型实现。"""

    def __init__(self, host: str = OLLAMA_HOST, model: str = LLM_MODEL,
                 timeout: float = REQUEST_TIMEOUT):
        self.client = ollama.AsyncClient(host=host, timeout=timeout)
        self.model = model

    async def generate(self, messages: list[dict]) -> str:
        """调用 Ollama 生成回答，空响应时自动重试一次。"""
        prompt_len = sum(len(m.get("content", "")) for m in messages)

        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.chat(
                    model=self.model,
                    messages=messages,
                    options={
                        "temperature": 0.3 if attempt == 0 else 0.5,
                        "num_predict": 512,
                        "repeat_penalty": 1.05,
                    },
                )
                content = response.get("message", {}).get("content", "")
                if content and content.strip():
                    return content

                logger.warning(
                    "模型 %s 返回空内容 (attempt %d/%d, prompt %d 字符)",
                    self.model, attempt + 1, MAX_RETRIES, prompt_len,
                )
            except Exception as e:
                logger.error("Ollama 调用失败 (attempt %d/%d): %s",
                             attempt + 1, MAX_RETRIES, e)
                if attempt == MAX_RETRIES - 1:
                    raise

        logger.error("模型 %s 连续 %d 次返回空内容，放弃重试", self.model, MAX_RETRIES)
        return ""


class DeepSeekProvider(LLMProvider):
    """DeepSeek API 实现。通过 OpenAI 兼容接口调用。

    openai 包采用延迟导入，避免 Ollama 用户因未安装而崩溃。
    """

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com",
                 model: str = "deepseek-chat", timeout: float = REQUEST_TIMEOUT):
        # 延迟导入：只在真正使用 DeepSeek 时才加载 openai 包
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "使用 DeepSeek 需要安装 openai 包: pip install openai"
            )
        self.client = AsyncOpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout,
        )
        self.model = model

    async def generate(self, messages: list[dict]) -> str:
        """调用 DeepSeek API 生成回答。"""
        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3 if attempt == 0 else 0.5,
                    max_tokens=1024,
                )
                content = response.choices[0].message.content
                if content and content.strip():
                    return content

                logger.warning("DeepSeek 返回空内容 (attempt %d/%d)",
                               attempt + 1, MAX_RETRIES)
            except Exception as e:
                logger.error("DeepSeek 调用失败 (attempt %d/%d): %s",
                             attempt + 1, MAX_RETRIES, e)
                if attempt == MAX_RETRIES - 1:
                    raise

        logger.error("DeepSeek 连续 %d 次返回空内容", MAX_RETRIES)
        return ""
