"""LLM client wrapper for TrinityGuard."""

import time
from abc import ABC, abstractmethod

from .exceptions import LLMError
from .llm_config import MASLLMConfig, MonitorLLMConfig, get_mas_llm_config, get_monitor_llm_config

# Module-level client cache: maps cache key -> BaseLLMClient instance
_client_cache: dict[str, "BaseLLMClient"] = {}


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    # Subclasses must set these for retry logic
    retry_count: int = 1
    retry_delay: float = 1.0

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        pass

    @abstractmethod
    def generate_with_system(self, system: str, user: str, **kwargs) -> str:
        """Generate with system and user messages."""
        pass

    def _generate_with_retry(self, generate_func, error_prefix: str = "LLM API", **kwargs) -> str:
        """Execute generate function with retry logic (shared by all subclasses)."""
        last_error = None
        for attempt in range(self.retry_count):
            try:
                return generate_func(**kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
        raise LLMError(f"{error_prefix} error after {self.retry_count} attempts: {str(last_error)}")


class OpenAIClient(BaseLLMClient):
    """OpenAI API client with retry and timeout support."""

    def __init__(self, config: MASLLMConfig | MonitorLLMConfig | None = None):
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

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        def _do_generate():
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            )
            content = response.choices[0].message.content
            # Return empty string if content is None
            return content if content is not None else ""

        return self._generate_with_retry(_do_generate, error_prefix="OpenAI API")

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
            content = response.choices[0].message.content
            # Return empty string if content is None
            return content if content is not None else ""

        return self._generate_with_retry(_do_generate, error_prefix="OpenAI API")


class AnthropicClient(BaseLLMClient):
    """Anthropic API client with retry support."""

    def __init__(self, config: MASLLMConfig | MonitorLLMConfig | None = None):
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

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        def _do_generate():
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature),
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            # Return empty string if text is None
            return text if text is not None else ""

        return self._generate_with_retry(_do_generate, error_prefix="Anthropic API")

    def generate_with_system(self, system: str, user: str, **kwargs) -> str:
        """Generate with system and user messages."""
        def _do_generate():
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature),
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            text = response.content[0].text
            # Return empty string if text is None
            return text if text is not None else ""

        return self._generate_with_retry(_do_generate, error_prefix="Anthropic API")


def get_llm_client(
    provider: str | None = None,
    config: MASLLMConfig | MonitorLLMConfig | None = None
) -> BaseLLMClient:
    """Get LLM client for MAS (default), with module-level caching.

    Args:
        provider: Optional provider override ("openai" or "anthropic")
        config: Optional config override (bypasses cache when provided)

    Returns:
        Configured LLM client
    """
    if config is None:
        config = get_mas_llm_config()
        resolved_provider = provider or config.provider
        cache_key = f"mas:{resolved_provider}"
        if cache_key not in _client_cache:
            _client_cache[cache_key] = _make_client(resolved_provider, config)
        return _client_cache[cache_key]

    # Custom config provided - do not cache
    resolved_provider = provider or config.provider
    return _make_client(resolved_provider, config)


def get_monitor_llm_client(provider: str | None = None) -> BaseLLMClient:
    """Get LLM client for Monitor agents with extended settings, with module-level caching.

    Args:
        provider: Optional provider override

    Returns:
        Configured LLM client with retry and timeout support
    """
    config = get_monitor_llm_config()
    resolved_provider = provider or config.provider
    cache_key = f"monitor:{resolved_provider}"
    if cache_key not in _client_cache:
        _client_cache[cache_key] = _make_client(resolved_provider, config)
    return _client_cache[cache_key]


def _make_client(provider: str, config: MASLLMConfig | MonitorLLMConfig) -> BaseLLMClient:
    """Instantiate the appropriate client for the given provider."""
    if provider == "openai":
        return OpenAIClient(config)
    elif provider == "anthropic":
        return AnthropicClient(config)
    else:
        raise LLMError(f"Unsupported LLM provider: {provider}")
