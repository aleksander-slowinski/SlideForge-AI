"""Bounded app-level retries for transient Gemini API errors.

Keep this module independent from the google-genai SDK so the core retry
logic can be tested without network calls or SDK client initialization.
"""
from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")

# Deliberately narrow. Do not retry invalid prompts, authentication, or
# Pydantic validation errors: fixing those requires changing inputs/code.
RETRYABLE_HTTP_CODES = frozenset({429, 503})


def api_error_status(error: BaseException) -> int | None:
    """Find the HTTP code through an SDK error wrapped with `raise ... from`.

    batch_content_service.generate_batch() wraps Google APIError as
    RuntimeError(... ) from original_error. We inspect the cause, not string
    fragments, to avoid retrying arbitrary RuntimeErrors mentioning '503'.
    """
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        code = getattr(current, "code", None)
        if isinstance(code, int) and not isinstance(code, bool):
            return code
        current = current.__cause__ or current.__context__
    return None


def call_with_retry(
    operation: Callable[[], T],
    *,
    attempts: int = 3,
    initial_delay: float = 3.0,
    max_delay: float = 20.0,
    jitter: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
    jitter_fn: Callable[[float, float], float] = random.uniform,
) -> T:
    """Retry HTTP 429/503 with capped exponential backoff and jitter.

    `attempts` includes the original call. After the final failure, re-raises
    the original exception without discarding its traceback or its cause.

    IMPORTANT: configure google-genai SDK with HttpRetryOptions(attempts=1)
    for clients passed to this service; otherwise SDK and application retries
    compound and can cause more remote requests than intended.
    """
    if isinstance(attempts, bool) or not isinstance(attempts, int) or not 1 <= attempts <= 5:
        raise ValueError("attempts musi wynosić od 1 do 5.")
    if initial_delay < 0 or max_delay < 0 or jitter < 0:
        raise ValueError("Opóźnienia retry nie mogą być ujemne.")

    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as error:
            status = api_error_status(error)
            if status not in RETRYABLE_HTTP_CODES or attempt == attempts:
                raise
            delay = min(max_delay, initial_delay * (2 ** (attempt - 1)) + jitter_fn(0.0, jitter))
            logger.warning(
                "Gemini HTTP %s — próba %s/%s nieudana; kolejne podejście za %.1f s.",
                status, attempt, attempts, delay,
            )
            sleep(delay)

    raise AssertionError("Unreachable: loop always returns or raises.")
