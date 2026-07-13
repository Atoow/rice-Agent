"""LLM 抽象层：定义统一接口，后续可切换 Ollama / DeepSeek / 通义千问。"""
from abc import ABC, abstractmethod
import ollama
from backend.config import OLLAMA_HOST, LLM_MODEL


class LLMProvider(ABC):
    """所有 LLM 后端的抽象基类。"""

    @abstractmethod
    async def generate(self, messages: list[dict]) -> str:
        """接收 messages（OpenAI 格式），返回生成的文本。"""
        ...


class OllamaProvider(LLMProvider):
    """Ollama 本地模型实现。"""

    def __init__(self, host: str = OLLAMA_HOST, model: str = LLM_MODEL):
        self.client = ollama.AsyncClient(host=host)
        self.model = model

    async def generate(self, messages: list[dict]) -> str:
        """调用 Ollama 生成回答，空响应时自动重试一次。"""
        prompt_len = sum(len(m.get("content", "")) for m in messages)

        for attempt in range(2):
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": 0.3 if attempt == 0 else 0.5,
                    "num_predict": 512,       # 强制至少尝试生成
                    "repeat_penalty": 1.05,   # 避免重复输出
                },
            )
            content = response.get("message", {}).get("content", "")
            if content and content.strip():
                return content

            print(f"[Ollama] 警告：模型 {self.model} 返回空内容 "
                  f"(attempt {attempt+1}/2, prompt {prompt_len} 字符)")

        print(f"[Ollama] 错误：模型 {self.model} 连续 2 次返回空内容，放弃重试")
        return ""


from openai import AsyncOpenAI


class DeepSeekProvider(LLMProvider):
    """DeepSeek API 实现。通过 OpenAI 兼容接口调用。"""

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com",
                 model: str = "deepseek-chat"):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def generate(self, messages: list[dict]) -> str:
        """调用 DeepSeek API 生成回答。"""
        for attempt in range(2):
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3 if attempt == 0 else 0.5,
                max_tokens=1024,
            )
            content = response.choices[0].message.content
            if content and content.strip():
                return content

            print(f"[DeepSeek] 警告：返回空内容 (attempt {attempt+1}/2)")

        print("[DeepSeek] 错误：连续 2 次返回空内容")
        return ""
