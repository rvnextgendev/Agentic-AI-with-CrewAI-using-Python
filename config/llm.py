"""Explicit LLM configuration for Groq and OpenAI-compatible providers."""

import os
import time
from config.environment import refresh_local_environment
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from openai import APIError, RateLimitError


refresh_local_environment()


class GroqReActChatModel(ChatOpenAI):
    """Bounded recovery without exposing failed or partial tool actions."""

    def _with_recovery(self, operation, messages):
        request_messages = list(messages)
        parse_retries = 0
        for attempt in range(4):
            try:
                return operation(request_messages)
            except APIError as exc:
                body = exc.body if isinstance(exc.body, dict) else {}
                error = body.get("error", body)
                code = error.get("code") if isinstance(error, dict) else None
                if code == "output_parse_failed" and parse_retries == 0 and attempt < 3:
                    parse_retries += 1
                    request_messages.append(HumanMessage(content=(
                        "The service could not parse the previous response. "
                        "Try again, following the original response format. "
                        "Return plain text only, without native function calls, "
                        "tool-call tags, or special control tokens. If the original "
                        "instructions require a tool action, write its Action and "
                        "Action Input fields as plain text with a valid JSON object "
                        "for the input; otherwise provide the requested final answer."
                    )))
                    print("Groq could not parse the response; retrying once with clearer formatting.", flush=True)
                    continue
                limited = isinstance(exc, RateLimitError) or "rate limit" in str(exc).lower()
                if not limited or attempt == 3:
                    raise
                print("Groq free-tier limit reached; waiting 65 seconds before retrying.", flush=True)
                time.sleep(65)

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        # Buffer before retrying so no partial action or callback is duplicated.
        chunks = self._with_recovery(
            lambda revised: list(super(GroqReActChatModel, self)._stream(
                revised, stop=stop, run_manager=None, **kwargs
            )), messages
        )
        for chunk in chunks:
            if run_manager:
                run_manager.on_llm_new_token(chunk.text, chunk=chunk)
            yield chunk

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._with_recovery(
            lambda revised: super(GroqReActChatModel, self)._generate(
                revised, stop=stop, run_manager=run_manager, **kwargs
            ), messages
        )


def validate_llm_key():
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    if provider == "groq" and os.getenv("LLM_MODEL", "").startswith("openai/gpt-oss"):
        raise ValueError(
            "GPT-OSS is incompatible with this legacy CrewAI text-tool setup. "
            "Set LLM_MODEL=qwen/qwen3.8-27b in .env or Streamlit secrets, then restart."
        )
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
