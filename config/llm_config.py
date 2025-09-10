"""
LLM Configuration settings for the service agent.
"""

from typing import Dict, Any
import os
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """Configuration for Language Learning Model settings."""
    
    # Local LLM settings (primary and only option)
    local_llm_url: str = "http://127.0.0.1:1234/v1"
    local_llm_model: str = "google/gemma-3-12b"
    local_llm_api_key: str = "not-needed"

    # General settings
    temperature: float = 0.2
    max_tokens: int = 4096
    timeout: int = 5
    
    # Chat history settings
    max_chat_history_length: int = 20
    preserve_system_message: bool = True

    def __post_init__(self):
        """Load configuration from environment variables if not provided."""
        # Override with environment variables if they exist
        self.local_llm_url = os.getenv("LOCAL_LLM_URL", self.local_llm_url)
        self.local_llm_model = os.getenv("LOCAL_LLM_MODEL", self.local_llm_model)
        self.temperature = float(os.getenv("LLM_TEMPERATURE", self.temperature))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", self.max_tokens))

    def get_config(self) -> Dict[str, Any]:
        """Get local LLM configuration."""
        return {
            "base_url": self.local_llm_url,
            "api_key": self.local_llm_api_key,
            "model": self.local_llm_model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    def get_provider_config(self, provider: str = "local") -> Dict[str, Any]:
        """Get configuration for a specific provider (local, langchain, etc.)."""
        if provider in ["local", "langchain"]:
            return self.get_config()
        else:
            raise ValueError(f"Unknown provider: {provider}")


# Global configuration instance
llm_config = LLMConfig()