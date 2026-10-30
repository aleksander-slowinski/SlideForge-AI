"""Isolated orchestration for SlideForge v1.1 Planned Generation.

Classic generation, SQL telemetry and the existing batch services are untouched.
"""

from __future__ import annotations

import os
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from pydantic import ValidationError

from models.planner_schemas import PresentationPlanSchema
from models.schemas import PresentationSchema
from services.batch_content_service import split_plan_into_batches
from services.resumable_batch_service import BatchCheckpointStore


@dataclass(frozen=True)
class PlannedArtifact:
    filename: str
    pptx_data: bytes
    slide_count: int
    quality_report: Any
    checkpoint_fingerprint: str


def load_presentation_plan(source: bytes | str) -> PresentationPlanSchema:
    """Read and validate the user-provided or locally stored JSON plan."""
    if isinstance(source, bytes):
        source = source.decode("utf-8-sig")
    return PresentationPlanSchema.model_validate_json(source)


def checkpoint_overview(
    plan: PresentationPlanSchema,
    *,
    checkpoint_root: str | Path,
    batch_size: int = 4,
) -> tuple[str, list[dict[str, Any]]]:
    """Inspect checkpoints WITHOUT calling Gemini or changing any files.

    Invalid checkpoints raise CheckpointError (fail closed), rather than being
    silently ignored or regenerated.
    """
    store = BatchCheckpointStore(checkpoint_root, plan, batch_size)
    rows = []
    for index, batch in enumerate(split_plan_into_batches(plan, batch_size), start=1):
        checkpoint = store.load(index, plan, batch)
        rows.append({
            "Partia": index,
            "Slajdy": f"{batch[0].slide_number}–{batch[-1].slide_number}",
            "Status": "Checkpoint HIT" if checkpoint is not None else "Do wygenerowania",
        })
    return store.fingerprint, rows


def _validate_generated_vs_plan(
    presentation: PresentationSchema,
    plan: PresentationPlanSchema,
) -> None:
    if presentation.slides_count != plan.slides_count or len(presentation.slides) != len(plan.slides):
        raise ValueError("Wygenerowana liczba slajdów nie odpowiada konspektowi.")
    if presentation.topic != plan.topic or presentation.language != "pl":
        raise ValueError("Wynik ma inny temat lub język niż konspekt.")
    for expected, actual in zip(plan.slides, presentation.slides):
        if (expected.slide_number != actual.slide_number or
                expected.layout != actual.layout or expected.title != actual.title):
            raise ValueError(f"Niezgodność z planem dla slajdu {expected.slide_number}.")


def _verify_pptx(path: Path, expected_content_slides: int) -> bytes:
    """Check that python-pptx produced a readable PPTX with a title slide."""
    from pptx import Presentation as PptxPresentation

    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Generator nie zapisał pliku PPTX.")
    with zipfile.ZipFile(path, "r") as archive:
        if archive.testzip() is not None or "ppt/presentation.xml" not in archive.namelist():
            raise ValueError("Wygenerowany plik PPTX jest uszkodzony.")
    rendered = PptxPresentation(str(path))
    if len(rendered.slides) != expected_content_slides + 1:
        raise ValueError(
            "Nieprawidłowa liczba slajdów w PPTX "
            f"({len(rendered.slides)} zamiast {expected_content_slides + 1})."
        )
    return path.read_bytes()


def build_planned_artifact(
    plan: PresentationPlanSchema,
    *,
    output_dir: str | Path,
    checkpoint_root: str | Path,
    batch_size: int = 4,
    client: Any = None,
    generate_fn: Callable[..., PresentationSchema] | None = None,
    render_fn: Callable[..., Any] | None = None,
    evaluate_fn: Callable[..., Any] | None = None,
    batch_event_handler: Callable[[dict], None] | None = None,
) -> PlannedArtifact:
    """Generate/reuse parts, validate full plan, render PPTX, evaluate quality.

    Optional injected functions allow comprehensive tests without Gemini API.
    Batch event callback is optional; Classic and offline tests stay unchanged.
    """
    if generate_fn is None:
        from services.resumable_batch_service import generate_content_resumable
        generate_fn = generate_content_resumable
    if render_fn is None:
        from services.ppt_service import create_presentation
        render_fn = create_presentation
    if evaluate_fn is None:
        from services.quality_v2_service import evaluate_presentation
        evaluate_fn = evaluate_presentation

    output_dir = Path(output_dir)
    store = BatchCheckpointStore(checkpoint_root, plan, batch_size)

    generate_kwargs = {
        "plan": plan,
        "batch_size": batch_size,
        "checkpoint_root": checkpoint_root,
        "client": client,
    }
    if batch_event_handler is not None:
        generate_kwargs["on_batch_event"] = batch_event_handler
    presentation = generate_fn(**generate_kwargs)
    if not isinstance(presentation, PresentationSchema):
        presentation = PresentationSchema.model_validate(presentation)
    _validate_generated_vs_plan(presentation, plan)

    # Do not overwrite an existing valid PPTX until a complete new render
    # has been validated. Failed runs leave prior outputs intact.
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"planned_{store.fingerprint[:16]}.pptx"
    tmp_path = output_dir / f".planned_{store.fingerprint[:16]}_{uuid.uuid4().hex}.pptx"
    try:
        render_fn(data=presentation, filename=str(tmp_path))
        payload = _verify_pptx(tmp_path, presentation.slides_count)
        quality_report = evaluate_fn(presentation)
        os.replace(tmp_path, output_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return PlannedArtifact(
        filename=output_path.name,
        pptx_data=payload,
        slide_count=presentation.slides_count,
        quality_report=quality_report,
        checkpoint_fingerprint=store.fingerprint,
    )
