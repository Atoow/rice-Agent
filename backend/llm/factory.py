"""LLM 工厂函数：根据配置创建对应的 Provider 实例。"""
import os
from backend.llm.provider import LLMProvider, OllamaProvider, DeepSeekProvider


def create_llm_provider() -> LLMProvider:
    """根据 LLM_PROVIDER 环境变量创建对应的 Provider。

    Returns:
        OllamaProvider 或 DeepSeekProvider 实例
    """
    provider_name = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider_name == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY 未设置，无法使用 DeepSeek")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        print(f"[LLM] 使用 DeepSeek API ({base_url})")
        return DeepSeekProvider(api_key=api_key, base_url=base_url)

    # 默认：Ollama
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("LLM_MODEL", "qwen2.5:3b")
    print(f"[LLM] 使用 Ollama ({host}, {model})")
    return OllamaProvider(host=host, model=model)
