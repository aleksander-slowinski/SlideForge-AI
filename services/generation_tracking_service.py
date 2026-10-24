
import logging
import re

from time import perf_counter

from models.schemas import PresentationSchema
from services import telemetry_service
from services.generation_metrics import GenerationMetrics
from services.quality_v2_service import evaluate_presentation


logger = logging.getLogger(__name__)


def get_error_code(error: Exception) -> str:
    message = str(error)

    match = re.search(r"\b(429|503)\b", message)

    if match:
        return match.group(1)

    return type(error).__name__[:30]


def save_metrics_safely(
    run_id: int | None,
    metrics: GenerationMetrics,
) -> None:
    """Nie przerywa aplikacji przy awarii SQL."""

    if run_id is None:
        return

    try:
        telemetry_service.save_run_metrics(
            run_id=run_id,
            metrics=metrics,
        )

    except Exception:
        logger.warning(
            "Nie udało się zapisać metryk modelu.",
            exc_info=True,
        )


def build_tracked_presentation(
    mode: str,
    topic: str,
    slides_count: int,
    output_path: str,
) -> PresentationSchema:

    if mode not in ("gemini", "demo"):
        raise ValueError(f"Nieznany tryb: {mode}")

    requested_slides = (
        4 if mode == "demo" else slides_count
    )

    generation_topic = (
        "SlideForge AI — Demonstracja"
        if mode == "demo"
        else topic
    )

    metrics = GenerationMetrics()

    start_time = perf_counter()
    run_id = None

    # ======================================
    # STARTED
    # ======================================

    try:
        run_id = telemetry_service.start_generation(
            mode=mode,
            topic=generation_topic,
            requested_slides=requested_slides,
        )

    except Exception:
        logger.warning(
            "Nie udało się zapisać STARTED.",
            exc_info=True,
        )

    # ======================================
    # GENERATION
    # ======================================

    try:
        if mode == "demo":
            from services.demo_service import (
                build_demo_presentation,
            )

            presentation = build_demo_presentation(
                output_path=output_path,
            )

        else:
            from services.presentation_service import (
                build_presentation,
            )

            presentation = build_presentation(
                topic=topic,
                slides_count=slides_count,
                output_path=output_path,
                metrics=metrics,
            )

    except Exception as error:
        duration_ms = int(
            (perf_counter() - start_time) * 1000
        )

        if run_id is not None:
            try:
                telemetry_service.fail_generation(
                    run_id=run_id,
                    duration_ms=duration_ms,
                    error_code=get_error_code(error),
                )

            except Exception:
                logger.warning(
                    "Nie udało się zapisać FAILED.",
                    exc_info=True,
                )

            if mode == "gemini":
                save_metrics_safely(run_id, metrics)

        raise

    # ======================================
    # SUCCESS
    # ======================================

    duration_ms = int(
        (perf_counter() - start_time) * 1000
    )

    if run_id is not None:
        try:
            telemetry_service.finish_generation(
                run_id=run_id,
                presentation=presentation,
                duration_ms=duration_ms,
            )

        except Exception:
            logger.warning(
                "Nie udało się zapisać SUCCESS.",
                exc_info=True,
            )

        else:
            try:
                quality_report = evaluate_presentation(
                    presentation
                )

                telemetry_service.save_quality_report(
                    run_id=run_id,
                    report=quality_report,
                )

            except Exception:
                logger.warning(
                    "Nie udało się zapisać Quality Report.",
                    exc_info=True,
                )

        if mode == "gemini":
            save_metrics_safely(run_id, metrics)

    return presentation
