"""
LLM Configuration settings for the service agent - AWS Bedrock version.
"""

from typing import Dict, Any
import os
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """Configuration for AWS Bedrock Language Learning Model settings."""
    
    # AWS Bedrock settings
    aws_region: str = "eu-central-1"  # Frankfurt - closest to Belgium
    model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"  # Claude 3.5 Sonnet

    # General settings
    temperature: float = 0.2
    max_tokens: int = 4096
    timeout: int = 30
    
    # Chat history settings
    max_chat_history_length: int = 20
    preserve_system_message: bool = True

    def __post_init__(self):
        """Load configuration from environment variables if not provided."""
        # AWS Bedrock settings
        self.aws_region = os.getenv("AWS_REGION", self.aws_region)
        self.model_id = os.getenv("BEDROCK_MODEL_ID", self.model_id)
        
        # General settings
        self.temperature = float(os.getenv("LLM_TEMPERATURE", self.temperature))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", self.max_tokens))

    def get_config(self) -> Dict[str, Any]:
        """Get AWS Bedrock configuration."""
        return {
            "region": self.aws_region,
            "model_id": self.model_id,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


# Global configuration instance
llm_config = LLMConfig()