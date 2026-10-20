"""Explicit LLM configuration for Groq and OpenAI-compatible providers."""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from openai import APIError, RateLimitError


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class GroqReActChatModel(ChatOpenAI):
    """Retry streamed rate limits before exposing any partial ReAct action."""

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        for attempt in range(4):
            try:
                # A stream may fail after starting. Buffer it so a retry cannot
                # duplicate partial actions in CrewAI's text parser or callbacks.
                chunks = list(super()._stream(
                    messages, stop=stop, run_manager=None, **kwargs
                ))
                for chunk in chunks:
                    if run_manager:
                        run_manager.on_llm_new_token(chunk.text, chunk=chunk)
                    yield chunk
                return
            except APIError as exc:
                limited = isinstance(exc, RateLimitError) or "rate limit" in str(exc).lower()
                if not limited or attempt == 3:
                    raise
                print("Groq free-tier limit reached; waiting 65 seconds before retrying.", flush=True)
                time.sleep(65)


def validate_llm_key():
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    name = "GROQ_API_KEY" if provider == "groq" else "OPENAI_API_KEY"
    key = os.getenv(name)
    if not key or key.startswith("your_"):
        raise ValueError(f"Set {name} in your .env file.")
    return key


def create_llm():
    groq = os.getenv("LLM_PROVIDER", "groq").lower() == "groq"
    model = os.getenv("LLM_MODEL", "qwen/qwen3.8-27b" if groq else "gpt-4")
    # CrewAI 0.28 uses text ReAct actions. GPT-OSS can emit native tool calls
    # instead, which Groq rejects when this legacy client sends no tool schemas.
    model_class = GroqReActChatModel if groq else ChatOpenAI
    return model_class(
        api_key=validate_llm_key(),
        base_url="https://api.groq.com/openai/v1" if groq else os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
        model=model,
        # Keep the completion budget for ReAct actions and final answers.
        model_kwargs={"extra_body": {"reasoning_effort": "none"}} if groq and model.startswith("qwen/") else {},
        temperature=0.5,
        max_tokens=768,
        max_retries=3,
        timeout=60,
    )
