"""
Qwen LLMs
"""
# pylint: disable=broad-exception-caught
import os
import logging
from dataclasses import dataclass
from typing import Dict, Union, Optional, Type, List
from openai import OpenAI
from pydantic_core import from_json
from dotenv import load_dotenv
from pydantic import BaseModel as PydanticBaseModel

from mcpuniverse.common.config import BaseConfig
from mcpuniverse.common.context import Context
from .base import BaseLLM

load_dotenv()


@dataclass
class QwenConfig(BaseConfig):
    """
    Configuration for Qwen language models.

    Attributes:
        model_name (str): Name of the Qwen model to use. Default is "qwen-plus".
        api_key (str): Qwen API key. Retrieved from QWEN_API_KEY environment variable.
        temperature (float): Controls randomness in output generation. Default is 1.0.
        top_p (float): Controls diversity of output generation. Default is 1.0.
        frequency_penalty (float): Reduces repetition of token sequences. Default is 0.0.
        presence_penalty (float): Encourages the model to talk about new topics. Default is 0.0.
        max_completion_tokens (int): Maximum number of tokens to generate. Default is 2048.
        seed (int): Seed for deterministic output generation. Default is 12345.
        base_url (str): Base URL for the Qwen API. Default is DashScope compatible endpoint.

    Note:
        For more information on available models, see:
        https://help.aliyun.com/zh/dashscope/developer-reference/model-introduction
    """
    model_name: str = "qwen-plus"  # qwen-plus, qwen-turbo, qwen-max, qwen-long
    api_key: str = os.getenv("QWEN_API_KEY", "")
    temperature: float = 1.0
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    max_completion_tokens: int = 2048
    seed: int = 12345


class QwenModel(BaseLLM):
    """
    Interacts with Qwen language models via DashScope API.

    This class provides methods for generating content using Qwen models,
    supporting both free-form text and structured output based on Pydantic models.

    Attributes:
        config_class (Type[QwenConfig]): Configuration class for Qwen models.
        alias (str): Short name for the model, set to "qwen".
    """
    config_class = QwenConfig
    alias = "qwen"
    env_vars = ["QWEN_API_KEY"]
    def __init__(self, config: Optional[Union[Dict, str]] = None):
        """
        Initializes the QwenModel instance.

        Args:
            config (Optional[Union[Dict, str]]): Configuration for the model.
                Can be a dictionary or a string. If None, default configuration is used.
        """
        super().__init__()
        self.config = QwenModel.config_class.load(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)

    def _generate(
            self,
            messages: List[dict[str, str]],
            response_format: Type[PydanticBaseModel] = None,
            **kwargs
    ):
        """
        Generates content using the Qwen model.

        Args:
            messages (List[dict[str, str]]): List of message dictionaries,
                each containing 'role' and 'content' keys.
            response_format (Type[PydanticBaseModel], optional): Pydantic model
                defining the structure of the desired output. If None, generates
                free-form text.
            **kwargs: Additional keyword arguments for the Qwen API.

        Returns:
            Union[str, PydanticBaseModel, None]: Generated content as a string
                if no response_format is provided, a Pydantic model instance if
                response_format is provided, or None if parsing structured output fails.
        """
        client = OpenAI(
            api_key=self.config.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
                    
        # Adjust parameters based on model version
        max_tokens = self._get_max_tokens_for_model()
        use_stream = self._should_use_stream_for_model()
        if response_format is None:
            api_params = {
                "messages": messages,
                "model": self.config.model_name,
                "temperature": self.config.temperature,
                "timeout": int(kwargs.get("timeout", 60)),
                "top_p": self.config.top_p,
                "frequency_penalty": self.config.frequency_penalty,
                "presence_penalty": self.config.presence_penalty,
                "seed": self.config.seed,
                "max_tokens": max_tokens,
                **kwargs
            }
            
            if use_stream:
                api_params["stream"] = True
                chat = client.chat.completions.create(**api_params)
                # Collect all chunks from stream
                content = ""
                for chunk in chat:
                    if chunk.choices[0].delta.content is not None:
                        content += chunk.choices[0].delta.content
                return content
            else:
                chat = client.chat.completions.create(**api_params)
                return chat.choices[0].message.content

        # For structured output, we need to use a different approach
        # since DashScope might not support response_format parameter
        try:
            # First try with response_format if supported
            api_params = {
                "messages": messages,
                "model": self.config.model_name,
                "temperature": self.config.temperature,
                "timeout": int(kwargs.get("timeout", 60)),
                "top_p": self.config.top_p,
                "frequency_penalty": self.config.frequency_penalty,
                "presence_penalty": self.config.presence_penalty,
                "seed": self.config.seed,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
                **kwargs
            }
            
            if use_stream:
                api_params["stream"] = True
                chat = client.chat.completions.create(**api_params)
                # Collect all chunks from stream
                content = ""
                for chunk in chat:
                    if chunk.choices[0].delta.content is not None:
                        content += chunk.choices[0].delta.content
                return response_format.model_validate(from_json(content))
            else:
                chat = client.chat.completions.create(**api_params)
                return response_format.model_validate(from_json(chat.choices[0].message.content))
        except Exception:
            # Fallback: add JSON format instruction to the prompt
            schema = response_format.model_json_schema()
            json_instruction = f"\n\nPlease respond with a valid JSON object matching this schema: {schema}"
            
            # Add instruction to the last user message
            if messages and messages[-1]["role"] == "user":
                messages[-1]["content"] += json_instruction
            else:
                messages.append({"role": "user", "content": json_instruction})
            
            api_params = {
                "messages": messages,
                "model": self.config.model_name,
                "temperature": self.config.temperature,
                "timeout": int(kwargs.get("timeout", 60)),
                "top_p": self.config.top_p,
                "frequency_penalty": self.config.frequency_penalty,
                "presence_penalty": self.config.presence_penalty,
                "seed": self.config.seed,
                "max_tokens": max_tokens,
                **kwargs
            }
            
            if use_stream:
                api_params["stream"] = True
                chat = client.chat.completions.create(**api_params)
                # Collect all chunks from stream
                content = ""
                for chunk in chat:
                    if chunk.choices[0].delta.content is not None:
                        content += chunk.choices[0].delta.content
                
                try:
                    return response_format.model_validate(from_json(content))
                except Exception:
                    self.logger.error("Failed to parse the output:\n%s", str(content))
                    return None
            else:
                chat = client.chat.completions.create(**api_params)
                try:
                    return response_format.model_validate(from_json(chat.choices[0].message.content))
                except Exception:
                    self.logger.error("Failed to parse the output:\n%s", str(chat.choices[0].message.content))
                    return None

    def _get_max_tokens_for_model(self) -> int:
        """Get the appropriate max_tokens value based on model version."""
        model_name = self.config.model_name.lower()
        
        # Different model versions have different limits
        if "qwen-max-0403" in model_name:
            # This version has strict limits
            return min(self.config.max_completion_tokens, 2000)
        elif "qwen-max-latest" in model_name or "qwen-max-0428" in model_name:
            # These versions might have different limits
            return min(self.config.max_completion_tokens, 4000)
        else:
            # Default conservative limit
            return min(self.config.max_completion_tokens, 2000)
    
    def _should_use_stream_for_model(self) -> bool:
        """Determine if stream mode should be used based on model version."""
        model_name = self.config.model_name.lower()
        
        # Some model versions require stream mode
        if "qwen-max-0403" in model_name:
            return True
        elif "qwen-max-latest" in model_name or "qwen-max-0428" in model_name:
            return False  # These might not require stream mode
        else:
            return True  # Default to stream mode for safety

    def set_context(self, context: Context):
        """
        Set context, e.g., environment variables (API keys).
        """
        super().set_context(context)
        self.config.api_key = context.env.get("QWEN_API_KEY", self.config.api_key)
