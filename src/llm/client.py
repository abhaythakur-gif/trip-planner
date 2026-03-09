"""
Centralized LLM client factory.
All agents that need an LLM should use get_llm() from here instead of
instantiating ChatOpenAI / ChatAnthropic directly.
"""

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from ..config import settings


def get_llm():
    """
    Return a configured LLM instance based on application settings.

    Uses settings.llm_provider to choose between OpenAI and Anthropic.
    All model/temperature/token settings are read from config automatically.

    Returns:
        ChatOpenAI or ChatAnthropic instance ready for use.
    """
    if settings.llm_provider == "openai":
        return ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.openai_api_key,
        )
    else:
        return ChatAnthropic(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.anthropic_api_key,
        )
