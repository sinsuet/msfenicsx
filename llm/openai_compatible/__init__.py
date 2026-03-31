"""OpenAI-compatible client boundary for union-LLM controller integrations."""

from llm.openai_compatible.client import OpenAICompatibleClient, OpenAICompatibleDecision
from llm.openai_compatible.config import OpenAICompatibleConfig
from llm.openai_compatible.replay import (
    load_request_trace,
    replay_request_trace_file,
    replay_request_trace_rows,
    save_replay_summary,
)

__all__ = [
    "OpenAICompatibleClient",
    "OpenAICompatibleConfig",
    "OpenAICompatibleDecision",
    "load_request_trace",
    "replay_request_trace_file",
    "replay_request_trace_rows",
    "save_replay_summary",
]
