"""
OpenAI LLMs
"""
# pylint: disable=broad-exception-caught
import os
from dataclasses import dataclass
from typing import Dict, Union, Optional, Type, List
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel as PydanticBaseModel

from mcpuniverse.common.config import BaseConfig
from mcpuniverse.common.context import Context
from .base import BaseLLM

load_dotenv()


@dataclass
class OpenRouterConfig(BaseConfig):
    """
    Configuration for OpenRouter language models.

    Attributes:
        model_name (str): The name of the OpenRouter model to use (default: "google/gemini-2.5-pro").
        api_key (str): The OpenRouter API key (default: environment variable    ).
        temperature (float): Controls randomness in output (default: 1.0).
        top_p (float): Controls diversity of output (default: 1.0).
        frequency_penalty (float): Penalizes frequent token use (default: 0.0).
        presence_penalty (float): Penalizes repeated topics (default: 0.0).
        max_completion_tokens (int): Maximum number of tokens in the completion (default: 2048).
        seed (int): Random seed for reproducibility (default: 12345).
    """
    model_name: str = "google/gemini-2.5-pro"
    api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    temperature: float = 1.0
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    max_completion_tokens: int = 2048
    seed: int = 12345


class OpenRouterModel(BaseLLM):
    """
         language models.

    This class provides methods to interact with OpenRouter's language models,
    including generating responses based on input messages.

    Attributes:
        config_class (Type[OpenRouterConfig]): Configuration class for the model.
        alias (str): Alias for the model, used for identification.
    """
    config_class = OpenRouterConfig
    alias = "openrouter"
    env_vars = ["OPENROUTER_API_KEY"]

    def __init__(self, config: Optional[Union[Dict, str]] = None):
        super().__init__()
        self.config = OpenRouterModel.config_class.load(config)
        self.total_cost = 0.0  # 跟踪总费用
        
        # 模型定价表 (价格每1K tokens)
        self.model_pricing = {
            # 最新模型价格
            "z-ai/glm-4.5v": {"input": 0.0005, "output": 0.0018},
            "moonshotai/kimi-k2": {"input": 0.00014, "output": 0.00249},
            "qwen/qwen3-235b-a22b": {"input": 0.00013, "output": 0.0006},
            "deepseek/deepseek-chat-v3.1": {"input": 0.0002, "output": 0.0008},
            "google/gemini-2.5-flash": {"input": 0.0003, "output": 0.0025},
            "x-ai/grok-4": {"input": 0.003, "output": 0.015},
            "google/gemini-2.5-pro": {"input": 0.00125, "output": 0.01},
            "openai/gpt-4.1": {"input": 0.002, "output": 0.008},
            
            # 其他常用模型
            "openai/gpt-4o": {"input": 0.0025, "output": 0.01},
            "openai/gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "anthropic/claude-3.5-sonnet": {"input": 0.003, "output": 0.015},
            "meta-llama/llama-3.1-8b-instruct": {"input": 0.00018, "output": 0.00018},
            "meta-llama/llama-3.1-70b-instruct": {"input": 0.00088, "output": 0.00088},
            "meta-llama/llama-3.1-405b-instruct": {"input": 0.003, "output": 0.003},
            "cohere/command-r-plus": {"input": 0.003, "output": 0.015},
            "mistralai/mixtral-8x7b-instruct": {"input": 0.00024, "output": 0.00024},
            "microsoft/wizardlm-2-8x22b": {"input": 0.00063, "output": 0.00063},
        }

    def _calculate_cost(self, usage, model_name):
        """计算费用"""
        if usage is None:
            return 0.0
        
        pricing = self.model_pricing.get(model_name, {"input": 0.001, "output": 0.002})
        
        prompt_tokens = usage.prompt_tokens if hasattr(usage, 'prompt_tokens') else 0
        completion_tokens = usage.completion_tokens if hasattr(usage, 'completion_tokens') else 0
        
        # 计算费用 (价格是每1K tokens)
        cost = (prompt_tokens / 1000 * pricing["input"]) + (completion_tokens / 1000 * pricing["output"])
        
        return cost

    def _generate(
            self,
            messages: List[dict[str, str]],
            response_format: Type[PydanticBaseModel] = None,
            **kwargs
    ):
        """
        Generates content using the OpenAI model.

        Args:
            messages (List[dict[str, str]]): List of message dictionaries,
                each containing 'role' and 'content' keys.
            response_format (Type[PydanticBaseModel], optional): Pydantic model
                defining the structure of the desired output. If None, generates
                free-form text.
            **kwargs: Additional keyword arguments.

        Returns:
            Union[str, PydanticBaseModel, None]: Generated content as a string
                if no response_format is provided, a Pydantic model instance if
                response_format is provided, or None if parsing structured output fails.
        """
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1", 
            api_key=self.config.api_key
        )
        if response_format is None:
            chat = client.chat.completions.create(
                messages=messages,
                model=self.config.model_name,
                temperature=self.config.temperature,
                timeout=int(kwargs.get("timeout", 60)),
                top_p=self.config.top_p,
                frequency_penalty=self.config.frequency_penalty,
                presence_penalty=self.config.presence_penalty,
                seed=self.config.seed,
                **kwargs
            )
            
            # 计算费用
            cost = self._calculate_cost(chat.usage, self.config.model_name)
            self.total_cost += cost
            
            # 显示费用信息
            print(f"本次调用费用: ${cost:.6f} | 总费用: ${self.total_cost:.6f}")
            
            return chat.choices[0].message.content

        chat = client.beta.chat.completions.parse(
            messages=messages,
            model=self.config.model_name,
            temperature=self.config.temperature,
            timeout=int(kwargs.get("timeout", 60)),
            top_p=self.config.top_p,
            frequency_penalty=self.config.frequency_penalty,
            presence_penalty=self.config.presence_penalty,
            seed=self.config.seed,
            response_format=response_format,
            **kwargs
        )
        
        # 计算费用
        cost = self._calculate_cost(chat.usage, self.config.model_name)
        self.total_cost += cost
        
        # 显示费用信息
        print(f"本次调用费用: ${cost:.6f} | 总费用: ${self.total_cost:.6f}")
        
        return chat.choices[0].message.parsed

    def get_total_cost(self):
        """获取总费用"""
        return self.total_cost
    
    def reset_cost(self):
        """重置费用计数"""
        self.total_cost = 0.0

    def set_context(self, context: Context):
        """
        Set context, e.g., environment variables (API keys).
        """
        super().set_context(context)
        self.config.api_key = context.env.get("OPENROUTER_API_KEY", self.config.api_key)