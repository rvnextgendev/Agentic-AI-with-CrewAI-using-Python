"""Safe user messages and redacted diagnostics for generation failures."""

import logging
import os
import re
import traceback
import uuid

from openai import AuthenticationError, PermissionDeniedError, RateLimitError, APIConnectionError, APITimeoutError
from pipeline import PipelineError


def report_failure(exc):
    reference = uuid.uuid4().hex[:12]
    details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    for name, value in os.environ.items():
        if value and len(value) > 5 and any(word in name.upper() for word in ("KEY", "TOKEN", "PASSWORD", "SECRET")):
            details = details.replace(value, "[REDACTED]")
    details = re.sub(r"gsk_[A-Za-z0-9]+|sk-(?:proj-)?[A-Za-z0-9_-]+", "[REDACTED]", details)
    logging.getLogger("post_studio").error("Generation failed [%s]\n%s", reference, details)
    if isinstance(exc, PipelineError):
        message = str(exc)
    elif isinstance(exc, AuthenticationError):
        message = "The API key was rejected. Check the key used by this UI: local .env or Cloud Secrets."
    elif isinstance(exc, PermissionDeniedError):
        message = "Groq denied model access. Enable qwen/qwen3.8-27b at https://console.groq.com/settings/project/limits."
    elif isinstance(exc, RateLimitError):
        message = "Groq's rate limit is still exceeded after retries. Wait a minute and retry; avoid running the CLI and UI together."
    elif isinstance(exc, (APIConnectionError, APITimeoutError)):
        message = "The AI service could not be reached or timed out. Check connectivity and retry."
    else:
        message = "Generation failed unexpectedly. Check the server log using the reference below. Completed stages remain available."
    return message, f"{type(exc).__name__} · Reference: {reference}"
