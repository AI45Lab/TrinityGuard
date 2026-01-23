"""LLM client wrapper for MASSafetyGuard."""

from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

from .config import get_config
from .exceptions import LLMError


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        pass

    @abstractmethod
    def generate_with_system(self, system: str, user: str, **kwargs) -> str:
        """Generate with system and user messages."""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        try:
            import openai
        except ImportError:
            raise LLMError("openai package not installed. Install with: pip install openai")

        config = get_config()
        self.api_key = api_key or config.llm.api_key
        self.model = model or config.llm.model

        if not self.api_key:
            raise LLMError(f"OpenAI API key not found. Set {config.llm.api_key_env} environment variable.")

        self.client = openai.OpenAI(api_key=self.api_key)

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise LLMError(f"OpenAI API error: {str(e)}")

    def generate_with_system(self, system: str, user: str, **kwargs) -> str:
        """Generate with system and user messages."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise LLMError(f"OpenAI API error: {str(e)}")


class AnthropicClient(BaseLLMClient):
    """Anthropic API client."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        try:
            import anthropic
        except ImportError:
            raise LLMError("anthropic package not installed. Install with: pip install anthropic")

        config = get_config()
        self.api_key = api_key or config.llm.api_key
        self.model = model or config.llm.model

        if not self.api_key:
            raise LLMError(f"Anthropic API key not found. Set {config.llm.api_key_env} environment variable.")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=get_config().llm.max_tokens,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            return response.content[0].text
        except Exception as e:
            raise LLMError(f"Anthropic API error: {str(e)}")

    def generate_with_system(self, system: str, user: str, **kwargs) -> str:
        """Generate with system and user messages."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=get_config().llm.max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                **kwargs
            )
            return response.content[0].text
        except Exception as e:
            raise LLMError(f"Anthropic API error: {str(e)}")


def get_llm_client(provider: Optional[str] = None) -> BaseLLMClient:
    """Get LLM client based on configuration."""
    config = get_config()
    provider = provider or config.llm.provider

    if provider == "openai":
        return OpenAIClient()
    elif provider == "anthropic":
        return AnthropicClient()
    else:
        raise LLMError(f"Unsupported LLM provider: {provider}")
