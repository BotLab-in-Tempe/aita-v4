# src/daser/configuration.py
"""Runtime configuration schema for the DASER LangGraph agent."""

from __future__ import annotations

from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig
import os
from dotenv import load_dotenv

load_dotenv(override=True)


class Configuration(BaseModel):
    """Runtime knobs exposed to LangGraph configurable."""

    # Model categories
    main_model: str = Field(
        default="openai:gpt-4o", description="Main LLM used by most nodes."
    )
    small_model: str = Field(
        default="openai:gpt-4o-mini", description="Lightweight LLM for simple tasks."
    )
    reasoning_model: str = Field(
        default="openai:gpt-5", description="Reasoning LLM for complex tasks (not currently used)."
    )
    
    # Token categories
    small_tokens: int = 1024
    medium_tokens: int = 2048
    large_tokens: int = 4096

    api_key: str = os.getenv("OPENAI_API_KEY")

    max_structured_output_retries: int = 3
    
    # Trace summarization
    trace_summarization_threshold: int = Field(
        default=15, description="Number of trace entries before summarization is triggered"
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
