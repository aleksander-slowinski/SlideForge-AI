"""SQL Server writes for planned runs; never stores slide content or prompts."""
from __future__ import annotations


def _connection():
    # Lazy import allows testing without ODBC drivers or local SQL Server.
    from services.db_service import get_connection
    return get_connection()


def start_planned_run(*, topic: str, slides_count: int,
                      fingerprint: str, batch_size: int) -> int:
    connection = _connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO dbo.GenerationRun
               (GenerationMode, GenerationStrategy, Topic, RequestedSlides,
                Status, CheckpointFingerprint, BatchSize)
               OUTPUT INSERTED.RunID
               VALUES ('gemini','planned',?,?,'STARTED',?,?)""",
            topic, slides_count, fingerprint, batch_size,
        )
        run_id = int(cursor.fetchone()[0])
        connection.commit()
        return run_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def record_batch(*, run_id: int, batch_index: int, slide_from: int,
                 slide_to: int, outcome: str, duration_ms: int,
                 api_calls: int, llm_duration_ms: int | None,
                 prompt_tokens: int | None, output_tokens: int | None,
                 thinking_tokens: int | None, total_tokens: int | None,
                 last_http_status: int | None) -> None:
    if outcome not in ('CHECKPOINT', 'GENERATED', 'FAILED'):
        raise ValueError('Nieprawidłowy status partii.')
    connection = _connection()
    try:
        cursor = connection.cursor()
        # Idempotent per RunID/BatchIndex, within one transaction.
        cursor.execute(
            "DELETE FROM dbo.PlannedBatchExecution WHERE RunID=? AND BatchIndex=?",
            run_id, batch_index,
        )
        cursor.execute(
            """INSERT INTO dbo.PlannedBatchExecution
               (RunID, BatchIndex, SlideFrom, SlideTo, Outcome,
                DurationMs, ApiCalls, LLMDurationMs, PromptTokens,
                OutputTokens, ThinkingTokens, TotalTokens, LastHttpStatus)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            run_id, batch_index, slide_from, slide_to, outcome,
            duration_ms, api_calls, llm_duration_ms, prompt_tokens,
            output_tokens, thinking_tokens, total_tokens, last_http_status,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def save_planned_counts(*, run_id: int, api_call_count: int,
                        checkpoint_hit_count: int) -> None:
    connection = _connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """UPDATE dbo.GenerationRun
               SET ApiCallCount=?, CheckpointHitCount=?
               WHERE RunID=? AND GenerationStrategy='planned'""",
            api_call_count, checkpoint_hit_count, run_id,
        )
        if cursor.rowcount != 1:
            raise ValueError('Nie znaleziono generowania Planned.')
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
