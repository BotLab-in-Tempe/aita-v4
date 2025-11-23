from __future__ import annotations

from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig
import os
from dotenv import load_dotenv

load_dotenv(override=True)


class Configuration(BaseModel):

    # Model categories
    main_model: str = Field(
        default="openai:gpt-4o", description="Main LLM used by most nodes."
    )
    small_model: str = Field(
        default="openai:gpt-4o-mini", description="Lightweight LLM for simple tasks."
    )
    reasoning_model: str = Field(
        default="openai:gpt-5",
        description="Reasoning LLM for complex tasks (not currently used).",
    )

    # Token categories
    small_tokens: int = 1024
    medium_tokens: int = 2048
    large_tokens: int = 4096

    api_key: str = os.getenv("OPENAI_API_KEY")

    max_structured_output_retries: int = 3

    # Trace summarization
    message_summarization_threshold: int = Field(
        default=15,
        description="Number of messages before summarization is triggered",
    )

    log_level: str = Field(
        default="INFO", description="Logging level for operational logs"
    )
    log_file_path: str = Field(
        default="logs/aita-ops.log", description="Path to operational log file"
    )
    log_max_bytes: int = Field(
        default=10485760, description="Maximum size of log file before rotation (10MB)"
    )
    log_backup_count: int = Field(
        default=5, description="Number of backup log files to keep"
    )

    class Config:
        arbitrary_types_allowed = True

    @staticmethod
    def from_runnable_config(config: RunnableConfig | None) -> "Configuration":
        if not config:
            return Configuration()
        cfg = config.get("configurable") or {}
        base = Configuration().model_dump()
        base.update({k: v for k, v in cfg.items() if k in base})
        return Configuration(**base)
