"""LLM client wrapper — 支持 OpenAI、Anthropic、DeepSeek，支持多 profile."""

import re
import time
from typing import Optional, Union
from abc import ABC, abstractmethod
import logging
import inspect
import os
import sys

from .llm_config import (
    get_mas_llm_config, get_monitor_llm_config,
    LLMProfile, MASLLMConfig, MonitorLLMConfig
)
from .exceptions import LLMError


class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def generate_with_system(self, system: str, user: str, **kwargs) -> str:
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI API 客户端."""

    def __init__(self, profile: LLMProfile):
        try:
            import openai
        except ImportError:
            raise LLMError("openai package not installed: pip install openai")

        self.profile = profile
        self.retry_count = getattr(profile, 'retry_count', 1)
        self.retry_delay = getattr(profile, 'retry_delay', 1.0)

        client_kwargs = {"api_key": profile.get_api_key()}
        if profile.base_url:
            client_kwargs["base_url"] = profile.base_url
        if profile.timeout:
            client_kwargs["timeout"] = profile.timeout

        self.client = openai.OpenAI(**client_kwargs)
        self.model = profile.model

    def _with_retry(self, fn):
        last_err = None
        for i in range(self.retry_count):
            try:
                return fn()
            except Exception as e:
                last_err = e
                if i < self.retry_count - 1:
                    time.sleep(self.retry_delay)
        raise LLMError(f"OpenAI error after {self.retry_count} retries: {last_err}")

    def generate(self, prompt: str, **kwargs) -> str:
        def _do():
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", self.profile.temperature),
                max_tokens=kwargs.get("max_tokens", self.profile.max_tokens),
            )
            return resp.choices[0].message.content or ""
        return self._with_retry(_do)

    def generate_with_system(self, system: str, user: str, **kwargs) -> str:
        def _do():
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=kwargs.get("temperature", self.profile.temperature),
                max_tokens=kwargs.get("max_tokens", self.profile.max_tokens),
            )
            return resp.choices[0].message.content or ""
        return self._with_retry(_do)


class AnthropicClient(BaseLLMClient):
    """Anthropic API 客户端."""

    def __init__(self, profile: LLMProfile):
        try:
            import anthropic
        except ImportError:
            raise LLMError("anthropic package not installed: pip install anthropic")

        self.profile = profile
        self.retry_count = getattr(profile, 'retry_count', 1)
        self.retry_delay = getattr(profile, 'retry_delay', 1.0)
        self.client = anthropic.Anthropic(api_key=profile.get_api_key())
        self.model = profile.model

    def _with_retry(self, fn):
        last_err = None
        for i in range(self.retry_count):
            try:
                return fn()
            except Exception as e:
                last_err = e
                if i < self.retry_count - 1:
                    time.sleep(self.retry_delay)
        raise LLMError(f"Anthropic error after {self.retry_count} retries: {last_err}")

    def generate(self, prompt: str, **kwargs) -> str:
        def _do():
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", self.profile.max_tokens),
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text or ""
        return self._with_retry(_do)

    def generate_with_system(self, system: str, user: str, **kwargs) -> str:
        def _do():
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", self.profile.max_tokens),
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return resp.content[0].text or ""
        return self._with_retry(_do)


class DeepSeekClient(BaseLLMClient):
    """DeepSeek API 客户端（OpenAI 兼容接口），支持 R1 推理模型."""

    def __init__(self, profile: LLMProfile):
        try:
            import openai
        except ImportError:
            raise LLMError("openai package not installed: pip install openai")

        self.profile = profile
        self.retry_count = getattr(profile, 'retry_count', 3)
        self.retry_delay = getattr(profile, 'retry_delay', 1.0)

        self.client = openai.OpenAI(
            api_key=profile.get_api_key(),
            base_url=profile.base_url or "https://api.deepseek.com/v1",
            timeout=profile.timeout or 120,
        )
        self.model = profile.model

    @staticmethod
    def _strip_think_tags(text: str) -> str:
        """去除 R1 输出中的 <think>...</think> 推理过程，只保留最终答案."""
        return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    def _with_retry(self, fn):
        last_err = None
        for i in range(self.retry_count):
            logging.getLogger(__name__).debug("DeepSeekClient _with_retry attempt %d/%d for model=%s", i+1, self.retry_count, getattr(self, 'model', None))
            try:
                return fn()
            except Exception as e:
                last_err = e
                logging.getLogger(__name__).warning("DeepSeekClient attempt %d failed: %s", i+1, str(e))
                if i < self.retry_count - 1:
                    time.sleep(self.retry_delay)
        raise LLMError(f"DeepSeek error after {self.retry_count} retries: {last_err}")

    def generate(self, prompt: str, **kwargs) -> str:
        def _do():
            logging.getLogger(__name__).debug("DeepSeekClient.generate START model=%s prompt_len=%d", getattr(self, 'model', None), len(prompt) if prompt is not None else 0)
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", self.profile.temperature),
                max_tokens=kwargs.get("max_tokens", self.profile.max_tokens),
            )
            # Primary content may be empty if the model spends tokens on reasoning.
            content = resp.choices[0].message.content or ""
            reasoning = getattr(resp.choices[0].message, 'reasoning_content', None) or ""
            out = self._strip_think_tags(content)

            # If out is empty, optionally auto-retry with a larger token budget
            auto_retry = os.environ.get("TRINITYGUARD_DEEPSEEK_AUTO_RETRY") in ("1", "true", "True")
            if not out:
                if auto_retry:
                    # Determine retry max tokens: bounded by profile.max_tokens and optional env cap
                    env_cap = os.environ.get("TRINITYGUARD_DEEPSEEK_RETRY_MAX_TOKENS")
                    try:
                        env_cap_val = int(env_cap) if env_cap is not None else None
                    except Exception:
                        env_cap_val = None
                    profile_max = getattr(self.profile, 'max_tokens', None) or None
                    if env_cap_val is not None and profile_max is not None:
                        retry_max_tokens = min(profile_max, env_cap_val)
                    elif env_cap_val is not None:
                        retry_max_tokens = env_cap_val
                    else:
                        retry_max_tokens = profile_max

                    logging.getLogger(__name__).info(
                        "DeepSeekClient: initial content empty, auto-retry enabled — retrying with max_tokens=%s",
                        retry_max_tokens,
                    )
                    try:
                        retry_resp = self.client.chat.completions.create(
                            model=self.model,
                            messages=[{"role": "user", "content": prompt}],
                            temperature=kwargs.get("temperature", self.profile.temperature),
                            max_tokens=retry_max_tokens,
                        )
                        retry_content = retry_resp.choices[0].message.content or ""
                        out = self._strip_think_tags(retry_content)
                        logging.getLogger(__name__).debug("DeepSeekClient.generate RETRY END model=%s out_len=%d", getattr(self, 'model', None), len(out) if out is not None else 0)
                    except Exception as e:
                        logging.getLogger(__name__).warning("DeepSeekClient auto-retry failed: %s", str(e))
                else:
                    # No auto-retry: fallback to returning the reasoning content (marked as potentially uncertain)
                    if reasoning:
                        logging.getLogger(__name__).warning("DeepSeekClient: content empty, returning reasoning_content as fallback (marked uncertain)")
                        out = reasoning.strip()

            logging.getLogger(__name__).debug("DeepSeekClient.generate END model=%s out_len=%d", getattr(self, 'model', None), len(out) if out is not None else 0)
            return out
        return self._with_retry(_do)

    def generate_with_system(self, system: str, user: str, **kwargs) -> str:
        def _do():
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=kwargs.get("temperature", self.profile.temperature),
                max_tokens=kwargs.get("max_tokens", self.profile.max_tokens),
            )
            return self._strip_think_tags(resp.choices[0].message.content or "")
        return self._with_retry(_do)


# ─── 工厂函数 ──────────────────────────────────────────────

def _make_client(profile: LLMProfile) -> BaseLLMClient:
    """根据 profile.provider 创建对应客户端."""
    if profile.provider == "openai":
        return OpenAIClient(profile)
    elif profile.provider == "anthropic":
        return AnthropicClient(profile)
    elif profile.provider == "deepseek":
        return DeepSeekClient(profile)
    else:
        raise LLMError(
            f"Unsupported provider: '{profile.provider}'. "
            "Supported: openai, anthropic, deepseek"
        )


def get_llm_client(agent_name: Optional[str] = None, config: Optional[Union[MASLLMConfig, LLMProfile]] = None, **kwargs) -> BaseLLMClient:
    """获取 MAS agent 的 LLM 客户端。

    Backwards-compatible wrapper: some older code calls `get_llm_client(config=...)`.
    We accept either a MASLLMConfig (container) or an LLMProfile (single profile).

    Args:
        agent_name: agent 名称，用于查找该 agent 的专属 profile。为 None 时使用 default profile。
        config: 可选的配置对象（MASLLMConfig 或 LLMProfile）。若提供，则使用该配置而不是全局加载器返回的配置。
    """
    # Temporary debug: log caller info and kwargs to help trace 'unexpected
    # keyword argument' issues. This is a short-lived debug aid; remove after
    # issue is diagnosed.
    logger = logging.getLogger(__name__)
    try:
        caller = inspect.stack()[1]
        caller_file = getattr(caller.frame, 'f_code', None)
        caller_path = caller_file.co_filename if caller_file is not None else None
    except Exception:
        caller_path = None
    # Standard debug log (subject to logging configuration)
    logger.debug("DEBUG get_llm_client invoked from: %s", caller_path)
    logger.debug(
        "DEBUG get_llm_client agent_name=%r config_type=%s kwargs=%r",
        agent_name,
        type(config).__name__ if config is not None else None,
        kwargs,
    )

    # Environment-gated stderr flush for reliable capture in CI / saved logs.
    # Set TRINITYGUARD_DEBUG_GET_LLM_CLIENT=1 to always emit a compact trace
    # to stderr regardless of logging config. This is intended for short-term
    # debugging and can be removed once the root cause is identified.
    try:
        if os.environ.get("TRINITYGUARD_DEBUG_GET_LLM_CLIENT") in ("1", "true", "True"):
            out = f"TRINITYGUARD DEBUG get_llm_client from={caller_path} agent_name={agent_name!r} config_type={type(config).__name__ if config is not None else None} kwargs={kwargs!r}\n"
            # write+flush to stderr to ensure it appears in redirected logs
            sys.stderr.write(out)
            sys.stderr.flush()
    except Exception:
        # Never let debug helper raise and interfere with normal flow
        logger.debug("Failed to emit TRINITYGUARD_DEBUG_GET_LLM_CLIENT stderr output")

    # If caller provided a config explicitly, use it (support legacy callers).
    # Accept **kwargs to be tolerant of older call sites that may pass
    # extra keyword arguments (e.g. `config` forwarded in unexpected ways).
    if config is not None:
        # MASLLMConfig: choose per-agent profile or default
        if isinstance(config, MASLLMConfig):
            profile = config.get_profile_for_agent(agent_name) if agent_name else config.default_profile
        # Direct LLMProfile: use it as-is
        elif isinstance(config, LLMProfile):
            profile = config
        else:
            # Unknown config shape: fall back to global loader
            cfg = get_mas_llm_config()
            profile = cfg.get_profile_for_agent(agent_name) if agent_name else cfg.default_profile
    else:
        # Normal path: load global MAS config
        cfg = get_mas_llm_config()
        profile = cfg.get_profile_for_agent(agent_name) if agent_name else cfg.default_profile

    return _make_client(profile)


def get_monitor_llm_client(monitor_name: Optional[str] = None) -> BaseLLMClient:
    """获取 Monitor agent 的 LLM 客户端。
    
    Args:
        monitor_name: monitor 名称，用于查找该 monitor 的专属 profile。
                      为 None 时使用 default profile。
    """
    config = get_monitor_llm_config()
    profile = config.get_profile_for_monitor(monitor_name) if monitor_name else config.default_profile
    return _make_client(profile)