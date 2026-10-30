"""Resumable generation for SlideForge's experimental batch pipeline.

Keeps existing batch_content_service untouched. Checkpoints are local JSON files
and should be stored in a Git-ignored directory (e.g. output/checkpoints).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from time import perf_counter
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from google import genai
from google.genai import types

from models.planner_schemas import PresentationPlanSchema
from models.schemas import PresentationSchema
from prompt_builder import get_system_prompt
from services.api_retry_service import call_with_retry, api_error_status
from services.batch_content_service import (
    BATCH_RULES,
    generate_batch,
    split_plan_into_batches,
)

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Increase when _build_batch_prompt(), generation semantics, or validation rules
# change in a way that makes previously saved outputs inappropriate to reuse.
PIPELINE_REVISION = "checkpoint-v1"


class CheckpointError(RuntimeError):
    """Existing checkpoint is invalid, incompatible, or unreadable."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


class BatchCheckpointStore:
    """A unique checkpoint folder for one plan and generation configuration."""

    def __init__(
        self,
        root: str | Path,
        plan: PresentationPlanSchema,
        batch_size: int,
    ) -> None:
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
        thinking_level = os.getenv("GEMINI_THINKING_LEVEL", "medium").strip().lower()
        self.fingerprint = _sha256(
            {
                "checkpoint_format": 1,
                "pipeline_revision": PIPELINE_REVISION,
                "plan": plan.model_dump(mode="json"),
                "batch_size": batch_size,
                "model_name": model_name,
                "thinking_level": thinking_level,
                "max_output_tokens": 16000,
                "system_instructions": get_system_prompt() + "\n" + BATCH_RULES,
            }
        )
        self.directory = Path(root) / self.fingerprint[:20]

    def path_for(self, batch_index: int) -> Path:
        return self.directory / f"batch_{batch_index:03d}.json"

    @staticmethod
    def _validate(
        result: PresentationSchema,
        plan: PresentationPlanSchema,
        batch: list,
    ) -> None:
        if result.topic != plan.topic:
            raise CheckpointError("Checkpoint ma inny temat prezentacji.")
        if result.language != "pl":
            raise CheckpointError("Checkpoint ma nieoczekiwany język.")
        if result.slides_count != len(batch):
            raise CheckpointError("Checkpoint ma nieprawidłową liczbę slajdów.")
        for local_number, (actual, expected) in enumerate(
            zip(result.slides, batch), start=1
        ):
            if (
                actual.slide_number != local_number
                or actual.title != expected.title
                or actual.layout != expected.layout
            ):
                raise CheckpointError(
                    f"Checkpoint nie odpowiada planowi (slajd {expected.slide_number})."
                )

    def load(
        self,
        batch_index: int,
        plan: PresentationPlanSchema,
        batch: list,
    ) -> PresentationSchema | None:
        path = self.path_for(batch_index)
        if not path.exists():
            return None

        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            expected_numbers = [slide.slide_number for slide in batch]
            if (
                envelope.get("fingerprint") != self.fingerprint
                or envelope.get("batch_index") != batch_index
                or envelope.get("global_slide_numbers") != expected_numbers
            ):
                raise CheckpointError("Checkpoint nie pasuje do bieżącej partii.")

            payload = envelope["presentation"]
            if envelope.get("content_sha256") != _sha256(payload):
                raise CheckpointError("Checkpoint ma niezgodną sumę kontrolną.")

            result = PresentationSchema.model_validate(payload)
            self._validate(result, plan, batch)
            return result
        except CheckpointError:
            raise
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise CheckpointError(
                f"Nie można odczytać checkpointu {path.name}. "
                "Nie zostanie automatycznie nadpisany."
            ) from exc

    def save(
        self,
        batch_index: int,
        plan: PresentationPlanSchema,
        batch: list,
        result: PresentationSchema,
    ) -> Path:
        # Validate before writing anything. The response has LOCAL numbering.
        self._validate(result, plan, batch)
        payload = result.model_dump(mode="json")
        envelope = {
            "fingerprint": self.fingerprint,
            "batch_index": batch_index,
            "global_slide_numbers": [s.slide_number for s in batch],
            "presentation": payload,
            "content_sha256": _sha256(payload),
        }
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.path_for(batch_index)
        temp_path: str | None = None
        try:
            # Same-directory temporary file + atomic replacement.
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.directory,
                prefix=".checkpoint_", suffix=".tmp", delete=False,
            ) as stream:
                temp_path = stream.name
                json.dump(envelope, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, target)
            return target
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)


def generate_content_resumable(
    plan: PresentationPlanSchema,
    batch_size: int = 4,
    checkpoint_root: str | Path = BASE_DIR / "output" / "checkpoints",
    client=None,
    on_batch_event: Callable[[dict], None] | None = None,
) -> PresentationSchema:
    """Generate or reuse validated batches, then validate the merged result.

    A failed API call does not delete earlier checkpoints. Restart with the
    same plan, batch size, model, thinking level and pipeline revision to resume.
    """
    batches = split_plan_into_batches(plan, batch_size=batch_size)
    store = BatchCheckpointStore(checkpoint_root, plan, batch_size)

    collected = []
    presentation_title: str | None = None
    owned_client = None

    def emit(kind: str, index: int, batch: list, duration_ms: int = 0,
             http_status: int | None = None) -> None:
        if on_batch_event is not None:
            on_batch_event({
                "kind": kind,
                "batch_index": index,
                "slide_from": batch[0].slide_number,
                "slide_to": batch[-1].slide_number,
                "duration_ms": duration_ms,
                "http_status": http_status,
            })

    try:
        for index, batch in enumerate(batches, start=1):
            batch_started = perf_counter()
            result = store.load(index, plan, batch)

            if result is not None:
                logger.info(
                    "Checkpoint HIT: batch %s/%s, slajdy %s-%s",
                    index, len(batches), batch[0].slide_number,
                    batch[-1].slide_number,
                )
                emit("CHECKPOINT", index, batch,
                     int((perf_counter() - batch_started) * 1000))
            else:
                if client is None and owned_client is None:
                    api_key = os.getenv("GEMINI_API_KEY")
                    if not api_key:
                        raise ValueError("Brak GEMINI_API_KEY w .env.")
                    owned_client = genai.Client(
                        api_key=api_key,
                        http_options=types.HttpOptions(
                            retry_options=types.HttpRetryOptions(attempts=1),
                        ),
                    )

                logger.info(
                    "Gemini API: batch %s/%s, slajdy %s-%s",
                    index, len(batches), batch[0].slide_number,
                    batch[-1].slide_number,
                )
                emit("START", index, batch)
                try:
                    result = call_with_retry(
                        lambda: generate_batch(
                            plan=plan,
                            batch=batch,
                            client=client if client is not None else owned_client,
                            previous_slides=collected,
                            presentation_title=presentation_title,
                        ),
                        attempts=3,
                        initial_delay=3.0,
                        max_delay=20.0,
                    )
                    path = store.save(index, plan, batch, result)
                except Exception as exc:
                    emit("FAILED", index, batch,
                         int((perf_counter() - batch_started) * 1000),
                         api_error_status(exc))
                    raise
                else:
                    emit("GENERATED", index, batch,
                         int((perf_counter() - batch_started) * 1000))
                    logger.info("Zapisano checkpoint: %s", path)

            if presentation_title is None:
                presentation_title = result.title
            elif result.title != presentation_title:
                raise CheckpointError(
                    "Niespójny tytuł pomiędzy zapisanymi partiami."
                )

            for actual, expected in zip(result.slides, batch):
                collected.append(
                    actual.model_copy(update={"slide_number": expected.slide_number})
                )
    finally:
        if owned_client is not None:
            owned_client.close()

    # Pydantic validates numbering, layout-specific fields and full slide count.
    return PresentationSchema.model_validate(
        {
            "title": presentation_title,
            "topic": plan.topic,
            "language": "pl",
            "slides_count": plan.slides_count,
            "slides": [s.model_dump(mode="json") for s in collected],
        }
    )
