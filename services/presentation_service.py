from models.schemas import PresentationSchema

from services.llm_service import generate_presentation
from services.ppt_service import create_presentation

from time import perf_counter
from services.generation_metrics import GenerationMetrics


def build_presentation(
    topic: str,
    slides_count: int,
    output_path: str,
    metrics: GenerationMetrics | None = None,
):
    # Generowanie i walidacja danych.
    if metrics is None:
        presentation = generate_presentation(
            topic=topic,
            slides_count=slides_count,
        )
    else:
        presentation = generate_presentation(
            topic=topic,
            slides_count=slides_count,
            metrics=metrics,
        )

    # Tworzenie pliku PPTX.
    pptx_start = perf_counter()

    try:
        create_presentation(
            data=presentation,
            filename=output_path,
        )
    finally:
        if metrics is not None:
            metrics.pptx_duration_ms = int(
                (perf_counter() - pptx_start) * 1000
            )

    return presentation
