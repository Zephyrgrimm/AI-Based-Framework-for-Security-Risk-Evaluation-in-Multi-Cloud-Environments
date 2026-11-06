"""LLM Provider Factory."""
from udge.core.config import config
from udge.llm.provider_base import BaseLLMProvider
from udge.llm.mock_provider import MockLLMProvider
from udge.llm.openai_provider import OpenAIProvider
from udge.llm.gemini_provider import GeminiProvider

def get_llm_provider(name: str = None) -> BaseLLMProvider:
    """Returns an instantiated LLM provider."""
    provider_name = (name or config.default_llm_provider).lower()

    if provider_name == "mock":
        return MockLLMProvider()
    elif provider_name in {"openai", "ollama"}:
        if provider_name == "ollama":
            return OpenAIProvider(
                api_key="ollama",
                model=config.ollama_model,
                base_url=f"{config.ollama_base_url}/v1"
            )
        if not config.openai_api_key:
            return MockLLMProvider()
        return OpenAIProvider(api_key=config.openai_api_key, model=config.openai_model)
    elif provider_name == "gemini":
        if not config.gemini_api_key:
            return MockLLMProvider()
        return GeminiProvider(api_key=config.gemini_api_key, model=config.gemini_model)

    return MockLLMProvider()
