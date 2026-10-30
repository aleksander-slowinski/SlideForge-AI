"""Tracked Planned Generation, keeping Classic mode completely unchanged.

The application can render PPTX even if SQL Server is unavailable. API usage is
measured from actual SDK calls, not inferred from planned batches. Failed API
calls may have unknown token consumption: no tokens are invented.
"""
from __future__ import annotations

import logging
import os
from collections import defaultdict
from pathlib import Path
from time import perf_counter
from typing import Any

from dotenv import load_dotenv

from models.planner_schemas import PresentationPlanSchema
from services.generation_metrics import GenerationMetrics
from services.generation_tracking_service import get_error_code
from services.resumable_batch_service import BatchCheckpointStore
from services import planned_telemetry_service, telemetry_service

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env', override=True)


def _ms(start: float) -> int:
    return max(0, round((perf_counter() - start) * 1000))


def _add_optional(current: int | None, additional: int | None) -> int | None:
    if additional is None:
        return current
    return (current or 0) + int(additional)


class MeteredGeminiClient:
    """Lazy google-genai client that records each outward generate_content call.

    The SDK has attempts=1 so three app-level retries mean at most three SDK
    invocations. When all batches are checkpoints, no SDK client is created.
    """
    def __init__(self, client: Any = None):
        self._client = client
        self._owned = False
        self.models = self
        self.active_batch: int | None = None
        self.calls = 0
        self.llm_duration_ms = 0
        self.tokens = {key: None for key in (
            'prompt_tokens', 'output_tokens', 'thinking_tokens', 'total_tokens')}
        self.per_batch = defaultdict(lambda: {
            'api_calls': 0, 'llm_duration_ms': 0,
            'prompt_tokens': None, 'output_tokens': None,
            'thinking_tokens': None, 'total_tokens': None,
            'last_http_status': None,
        })

    def _get_client(self):
        if self._client is None:
            from google import genai
            from google.genai import types
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError('Brak GEMINI_API_KEY w pliku .env.')
            self._client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
            self._owned = True
        return self._client

    def generate_content(self, **kwargs):
        from services.api_retry_service import api_error_status
        client = self._get_client()
        batch_id = self.active_batch
        stats = self.per_batch[batch_id]
        stats['api_calls'] += 1
        self.calls += 1
        started = perf_counter()
        try:
            response = client.models.generate_content(**kwargs)
        except Exception as exc:
            stats['last_http_status'] = api_error_status(exc)
            raise
        else:
            stats['last_http_status'] = None
            usage = getattr(response, 'usage_metadata', None)
            if usage is not None:
                mapping = {
                    'prompt_tokens': 'prompt_token_count',
                    'output_tokens': 'candidates_token_count',
                    'thinking_tokens': 'thoughts_token_count',
                    'total_tokens': 'total_token_count',
                }
                for target, field in mapping.items():
                    value = getattr(usage, field, None)
                    stats[target] = _add_optional(stats[target], value)
                    self.tokens[target] = _add_optional(self.tokens[target], value)
            return response
        finally:
            elapsed = _ms(started)
            stats['llm_duration_ms'] += elapsed
            self.llm_duration_ms += elapsed

    def close(self):
        if self._owned and self._client is not None:
            self._client.close()


def _safe_sql(operation, *args, **kwargs):
    try:
        return operation(*args, **kwargs)
    except Exception:
        logger.warning('Planned telemetry SQL unavailable: %s', operation.__name__,
                       exc_info=True)
        return None


def build_tracked_planned_artifact(
    plan: PresentationPlanSchema,
    *,
    output_dir: str | Path,
    checkpoint_root: str | Path,
    batch_size: int = 4,
    client: Any = None,
    generate_fn=None,
    render_fn=None,
    evaluate_fn=None,
):
    """Run tracked Planned pipeline; SQL failures never prevent generation.

    A new RunID represents a new user invocation. Checkpoints from past runs
    count as CACHE hits, not newly generated slides or API token usage.
    """
    from services.planned_presentation_service import build_planned_artifact
    if render_fn is None:
        from services.ppt_service import create_presentation as render_fn

    started = perf_counter()
    store = BatchCheckpointStore(checkpoint_root, plan, batch_size)
    run_id = _safe_sql(
        planned_telemetry_service.start_planned_run,
        topic=plan.topic,
        slides_count=plan.slides_count,
        fingerprint=store.fingerprint,
        batch_size=batch_size,
    )
    metered = MeteredGeminiClient(client)
    checkpoint_hits = 0
    pptx_duration_ms = None
    captured_presentation = {"data": None}

    def on_batch_event(event: dict):
        nonlocal checkpoint_hits
        kind = event['kind']
        batch_index = event['batch_index']
        if kind == 'START':
            metered.active_batch = batch_index
            return
        if kind == 'CHECKPOINT':
            checkpoint_hits += 1
        stats = metered.per_batch.get(batch_index, {})
        if run_id is not None:
            _safe_sql(
                planned_telemetry_service.record_batch,
                run_id=run_id,
                batch_index=batch_index,
                slide_from=event['slide_from'],
                slide_to=event['slide_to'],
                outcome=kind,
                duration_ms=event['duration_ms'],
                api_calls=stats.get('api_calls', 0),
                llm_duration_ms=(stats.get('llm_duration_ms') if kind != 'CHECKPOINT' else None),
                prompt_tokens=stats.get('prompt_tokens'),
                output_tokens=stats.get('output_tokens'),
                thinking_tokens=stats.get('thinking_tokens'),
                total_tokens=stats.get('total_tokens'),
                last_http_status=event.get('http_status') or stats.get('last_http_status'),
            )

    def measured_renderer(*, data, filename):
        nonlocal pptx_duration_ms
        captured_presentation["data"] = data
        started_render = perf_counter()
        try:
            render_fn(data=data, filename=filename)
        finally:
            pptx_duration_ms = _ms(started_render)

    def save_partial_metrics():
        if run_id is None:
            return
        _safe_sql(planned_telemetry_service.save_planned_counts,
                  run_id=run_id, api_call_count=metered.calls,
                  checkpoint_hit_count=checkpoint_hits)
        metrics = GenerationMetrics(
            model_name=os.getenv('GEMINI_MODEL', 'gemini-3.8-flash'),
            thinking_level=os.getenv('GEMINI_THINKING_LEVEL', 'medium'),
            llm_duration_ms=metered.llm_duration_ms if metered.calls else None,
            validation_duration_ms=None,  # not measured separately in Planned
            pptx_duration_ms=pptx_duration_ms,
            **metered.tokens,
        )
        _safe_sql(telemetry_service.save_run_metrics, run_id=run_id, metrics=metrics)

    try:
        artifact = build_planned_artifact(
            plan=plan, output_dir=output_dir,
            checkpoint_root=checkpoint_root, batch_size=batch_size,
            client=metered,
            render_fn=measured_renderer,
            batch_event_handler=on_batch_event,
            generate_fn=generate_fn,
            evaluate_fn=evaluate_fn,
        )
    except Exception as exc:
        if run_id is not None:
            _safe_sql(telemetry_service.fail_generation,
                      run_id=run_id, duration_ms=_ms(started),
                      error_code=get_error_code(exc))
        save_partial_metrics()
        raise
    else:
        if run_id is not None:
            # Only after PPTX validation, never mark partial batches SUCCESS.
            try:
                telemetry_service.finish_generation(
                    run_id=run_id,
                    presentation=captured_presentation['data'],
                    duration_ms=_ms(started),
                )
            except Exception:
                logger.warning('Cannot finalize Planned RunID=%s', run_id, exc_info=True)
            else:
                _safe_sql(
                    telemetry_service.save_quality_report,
                    run_id=run_id,
                    report=artifact.quality_report,
                )
        save_partial_metrics()
        return artifact
    finally:
        metered.close()
