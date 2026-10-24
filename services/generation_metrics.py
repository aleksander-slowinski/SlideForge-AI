
from dataclasses import dataclass


@dataclass
class GenerationMetrics:
    model_name: str | None = None
    thinking_level: str | None = None

    llm_duration_ms: int | None = None
    validation_duration_ms: int | None = None
    pptx_duration_ms: int | None = None

    prompt_tokens: int | None = None
    output_tokens: int | None = None
    thinking_tokens: int | None = None
    total_tokens: int | None = None
