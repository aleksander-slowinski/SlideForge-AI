
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types, errors

from models.schemas import PresentationSchema
from prompt_builder import (
    get_system_prompt,
    build_user_prompt,
)

from time import perf_counter
from services.generation_metrics import GenerationMetrics

# ==========================================
# KONFIGURACJA GEMINI API
# ==========================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "Brak klucza GEMINI_API_KEY w pliku .env!"
    )

# Maksymalnie 3 próby dla błędu 503
client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=3,
            initial_delay=2.0,
            max_delay=8.0,
            exp_base=2.0,
            jitter=1.0,
            http_status_codes=[503],
        )
    ),
)


# ==========================================
# GENEROWANIE PREZENTACJI
# ==========================================

def generate_presentation(
    topic: str,
    slides_count: int,
    metrics: GenerationMetrics | None = None,
) -> PresentationSchema:

    model_name = os.getenv(
        "GEMINI_MODEL", "gemini-3.6-flash"
    ).strip()

    thinking_level = os.getenv(
        "GEMINI_THINKING_LEVEL", "medium"
    ).strip().lower()

    if metrics is not None:
        metrics.model_name = model_name
        metrics.thinking_level = thinking_level

    supported_models = {
        "gemini-3.6-flash",
        "gemini-3.8-flash",
        "gemini-4-argon",
    }

    if model_name not in supported_models:
        raise ValueError(f"Nieobsługiwany model: {model_name}")

    if thinking_level not in {"low", "medium", "high"}:
        raise ValueError("Thinking level musi być low, medium lub high.")

    user_prompt = build_user_prompt(
        topic=topic,
        slides_count=slides_count,
    )

    config = types.GenerateContentConfig(
        system_instruction=get_system_prompt(),
        response_mime_type="application/json",
        max_output_tokens=32768,
        thinking_config=types.ThinkingConfig(
            thinking_level=thinking_level
        ),
    )

    # Wywołanie API z automatycznym retry

    llm_start = perf_counter()

    try:
        response = client.models.generate_content(
            model=  model_name,
            contents=user_prompt,
            config=config,
        )

    except errors.ServerError as exc:
        if exc.code == 503:
            raise RuntimeError(
                "Gemini jest obecnie przeciążone (503). "
                "Wykonano maksymalnie 3 próby. "
                "Spróbuj ponownie później."
            ) from exc
        raise

    except errors.ClientError as exc:
        if exc.code == 429:
            raise RuntimeError(
                "Gemini zwrócił błąd limitu żądań (429). "
                "Sprawdź dostępny limit API."
            ) from exc
        raise
    finally:
        if metrics is not None:
            metrics.llm_duration_ms = int(
                (perf_counter() - llm_start) * 1000
            )


    if metrics is not None:
        usage = getattr(response, "usage_metadata", None)

        if usage is not None:
            metrics.prompt_tokens = getattr(
                usage, "prompt_token_count", None
            )
            metrics.output_tokens = getattr(
                usage, "candidates_token_count", None
            )
            metrics.thinking_tokens = getattr(
                usage, "thoughts_token_count", None
            )
            metrics.total_tokens = getattr(
                usage, "total_token_count", None
            )

    # Walidacja odpowiedzi
    if not response.text:
        raise ValueError(
            "Gemini zwrócił pustą odpowiedź."
        )

    validation_start = perf_counter()

    try:
        return PresentationSchema.model_validate_json(response.text)
    finally:
        if metrics is not None:
            metrics.validation_duration_ms = int(
                (perf_counter() - validation_start) * 1000
            )
