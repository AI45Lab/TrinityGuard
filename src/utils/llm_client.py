"""LLM client wrapper for MASSafetyGuard."""

import time
from typing import Optional, Union
from abc import ABC, abstractmethod

from .llm_config import (
    get_llm_config, get_mas_llm_config, get_monitor_llm_config,
    LLMConfig, MASLLMConfig, MonitorLLMConfig
)
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
    """OpenAI API client with retry and timeout support."""

    def __init__(self, config: Optional[Union[MASLLMConfig, MonitorLLMConfig]] = None):
        """Initialize OpenAI client.

        Args:
            config: Optional config. If not provided, loads MAS config by default.
        """
        try:
            import openai
        except ImportError:
            raise LLMError("openai package not installed. Install with: pip install openai")

        self.config = config or get_mas_llm_config()

        # Get extended settings if MonitorLLMConfig
        self.retry_count = getattr(self.config, 'retry_count', 1)
        self.retry_delay = getattr(self.config, 'retry_delay', 1.0)
        self.timeout = getattr(self.config, 'timeout', None)

        # Create client with optional base_url and timeout
        client_kwargs = {"api_key": self.config.get_api_key()}
        if self.config.base_url:
            client_kwargs["base_url"] = self.config.base_url
        if self.timeout:
            client_kwargs["timeout"] = self.timeout

        self.client = openai.OpenAI(**client_kwargs)
        self.model = self.config.model

    def _generate_with_retry(self, generate_func, **kwargs) -> str:
        """Execute generate function with retry logic."""
        last_error = None
        for attempt in range(self.retry_count):
            try:
                return generate_func(**kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
        raise LLMError(f"OpenAI API error after {self.retry_count} attempts: {str(last_error)}")

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        def _do_generate():
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            )
            return response.choices[0].message.content

        return self._generate_with_retry(_do_generate)

    def generate_with_system(self, system: str, user: str, **kwargs) -> str:
        """Generate with system and user messages."""
        def _do_generate():
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

        return self._generate_with_retry(_do_generate)


class AnthropicClient(BaseLLMClient):
    """Anthropic API client with retry support."""

    def __init__(self, config: Optional[Union[MASLLMConfig, MonitorLLMConfig]] = None):
        """Initialize Anthropic client."""
        try:
            import anthropic
        except ImportError:
            raise LLMError("anthropic package not installed. Install with: pip install anthropic")

        self.config = config or get_mas_llm_config()

        # Get extended settings if MonitorLLMConfig
        self.retry_count = getattr(self.config, 'retry_count', 1)
        self.retry_delay = getattr(self.config, 'retry_delay', 1.0)

        self.client = anthropic.Anthropic(api_key=self.config.get_api_key())
        self.model = self.config.model

    def _generate_with_retry(self, generate_func, **kwargs) -> str:
        """Execute generate function with retry logic."""
        last_error = None
        for attempt in range(self.retry_count):
            try:
                return generate_func(**kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
        raise LLMError(f"Anthropic API error after {self.retry_count} attempts: {str(last_error)}")

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        def _do_generate():
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        return self._generate_with_retry(_do_generate)

    def generate_with_system(self, system: str, user: str, **kwargs) -> str:
        """Generate with system and user messages."""
        def _do_generate():
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text

        return self._generate_with_retry(_do_generate)


def get_llm_client(
    provider: Optional[str] = None,
    config: Optional[Union[MASLLMConfig, MonitorLLMConfig]] = None
) -> BaseLLMClient:
    """Get LLM client for MAS (default).

    Args:
        provider: Optional provider override ("openai" or "anthropic")
        config: Optional config override

    Returns:
        Configured LLM client
    """
    if config is None:
        config = get_mas_llm_config()

    provider = provider or config.provider

    if provider == "openai":
        return OpenAIClient(config)
    elif provider == "anthropic":
        return AnthropicClient(config)
    else:
        raise LLMError(f"Unsupported LLM provider: {provider}")


def get_monitor_llm_client(provider: Optional[str] = None) -> BaseLLMClient:
    """Get LLM client for Monitor agents with extended settings.

    Args:
        provider: Optional provider override

    Returns:
        Configured LLM client with retry and timeout support
    """
    config = get_monitor_llm_config()
    provider = provider or config.provider

    if provider == "openai":
        return OpenAIClient(config)
    elif provider == "anthropic":
        return AnthropicClient(config)
    else:
        raise LLMError(f"Unsupported LLM provider: {provider}")
