"""LLM client wrapper for MASSafetyGuard."""

from typing import Optional
from abc import ABC, abstractmethod

from .llm_config import get_llm_config, LLMConfig
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

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize OpenAI client.

        Args:
            config: Optional LLMConfig. If not provided, loads from llm_config.yaml
        """
        try:
            import openai
        except ImportError:
            raise LLMError("openai package not installed. Install with: pip install openai")

        self.config = config or get_llm_config()

        # Create client with optional base_url
        client_kwargs = {"api_key": self.config.get_api_key()}
        if self.config.base_url:
            client_kwargs["base_url"] = self.config.base_url

        self.client = openai.OpenAI(**client_kwargs)
        self.model = self.config.model

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
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
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            )
            return response.choices[0].message.content
        except Exception as e:
            raise LLMError(f"OpenAI API error: {str(e)}")


class AnthropicClient(BaseLLMClient):
    """Anthropic API client."""

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize Anthropic client."""
        try:
            import anthropic
        except ImportError:
            raise LLMError("anthropic package not installed. Install with: pip install anthropic")

        self.config = config or get_llm_config()
        self.client = anthropic.Anthropic(api_key=self.config.get_api_key())
        self.model = self.config.model

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            raise LLMError(f"Anthropic API error: {str(e)}")

    def generate_with_system(self, system: str, user: str, **kwargs) -> str:
        """Generate with system and user messages."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text
        except Exception as e:
            raise LLMError(f"Anthropic API error: {str(e)}")


def get_llm_client(provider: Optional[str] = None, config: Optional[LLMConfig] = None) -> BaseLLMClient:
    """Get LLM client based on configuration.

    Args:
        provider: Optional provider override ("openai" or "anthropic")
        config: Optional LLMConfig override

    Returns:
        Configured LLM client
    """
    if config is None:
        config = get_llm_config()

    provider = provider or config.provider

    if provider == "openai":
        return OpenAIClient(config)
    elif provider == "anthropic":
        return AnthropicClient(config)
    else:
        raise LLMError(f"Unsupported LLM provider: {provider}")
