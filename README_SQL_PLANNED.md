# SlideForge AI v1.1 — Planned SQL Telemetry

## What this update changes

Works with the existing v1.1 checkpoint + retry + Streamlit Planned Generation patches. Does not modify Classic mode, `app.py`, `batch_content_service.py`, or existing Pydantic schemas.

- Existing `GenerationRun` remains the run header, with `GenerationMode='gemini'` and **new** `GenerationStrategy='planned'`. Existing records default to `'classic'`.
- Each batch receives one row in `PlannedBatchExecution`: `GENERATED`, `CHECKPOINT`, or `FAILED`. A failed 503 batch is recorded, while complete checkpoint batches are marked `CHECKPOINT` with zero SDK requests.
- Captures the number of `models.generate_content` SDK calls, elapsed SDK call time, retry/backoff-inclusive batch time, and token usage **only when the SDK provides usage metadata**. Unknown usage is NULL.
- Existing `finish_generation` saves successful slides, and `save_quality_report` saves the score when the final PPTX is valid. A partial run is `FAILED` and has no artificial `GeneratedSlides` / quality score.
- Continues to produce PPTX when SQL Server is unavailable.

## Install

1. In VS Code open SlideForge on `feature/long-presentations`. Keep a commit or backup before overwriting files.
2. Run `sql/planned_telemetry.sql` in **SSMS against SlideForgeDB**. It alters `GenerationRun`, creates `PlannedBatchExecution`, updates `vw_GenerationAnalytics`, and creates `vw_PlannedBatchAnalytics`.
3. Merge this patch into the root of your existing SlideForge project. It updates **three existing files**:
   - `services/resumable_batch_service.py`
   - `services/planned_presentation_service.py`
   - `pages/1_Planned_Generation.py`
   And adds:
   - `services/planned_telemetry_service.py`
   - `services/planned_tracking_service.py`
   - `tests/test_planned_tracking.py`
   - `sql/planned_telemetry.sql`
   - `scripts/dev_test_planned_sql.py` (optional smoke test without Gemini)
4. In the activated Python environment:

```powershell
python -m pytest tests/test_planned_tracking.py -v
python -m pytest -q
python -m streamlit run app.py
```

## Verify SQL without calling Gemini at all

After applying the migration, run once:

```powershell
python -m scripts.dev_test_planned_sql
```

The script inserts a visibly marked `[TEST]` run with a synthetic failed batch (3 SDK attempts, `503`, no token usage). It exercises the **real SQL connection and the schema** but does **not** make network requests to Google. Your existing Power BI `IsTest=False` filter will exclude it.

## Verify even with persistent HTTP 503

Open Planned Generation and click **Generuj / wznów prezentację** once. If the provider returns 503 on all three attempts, the UI should show the warning and the database should have a `FAILED` run with `GenerationStrategy='planned'`, `ApiCallCount=3`, `CheckpointHitCount=0`, and one `PlannedBatchExecution` row for batch 1 with `Outcome='FAILED'`, `ApiCalls=3`, `LastHttpStatus=503`. Values may differ if the provider succeeds or a checkpoint is already present.

```sql
USE SlideForgeDB;
SELECT TOP (10) RunID, GenerationMode, GenerationStrategy, Status,
    RequestedSlides, GeneratedSlides, ErrorCode, DurationMs,
    ApiCallCount, CheckpointHitCount, ModelName, TotalTokens
FROM dbo.GenerationRun ORDER BY RunID DESC;

SELECT TOP (20) RunID, BatchIndex, SlideFrom, SlideTo, Outcome,
    ApiCalls, LastHttpStatus, DurationMs, LLMDurationMs, TotalTokens
FROM dbo.PlannedBatchExecution ORDER BY RunID DESC, BatchIndex;
```

When Gemini is available, completed runs will create `GeneratedSlide` and `GenerationQuality` entries as before. Another run with the same plan/configuration will use checkpoints (no new API calls for those batches).

## Measurement interpretation

- `DurationMs` (GenerationRun): whole user invocation, including retries, waits, rendering and SQL overhead.
- `LLMDurationMs`: sum of elapsed SDK calls, including failed calls, *excluding* backoff delays.
- `ApiCallCount`: count of SDK `models.generate_content` invocations. The SDK is configured with `attempts=1` in this pipeline to prevent nested retries. Does not represent internal model computation.
- `TotalTokens`: sum of token metadata reported by **successful API responses** in the current invocation. Failed calls may lack usage metadata, so figures can be incomplete. Checkpoint reuses do not count historical tokens in the new run.
- `ValidationDurationMs`: NULL for Planned Generation in this version (not separately instrumented).
- Planner was run previously and imported via JSON, so Planner API duration/tokens are not captured in this run. Do not infer them from batch data.

## Limits

- The SQL script updates `vw_GenerationAnalytics` based on the view definition used in Sprint 9.3. If you've customized the view locally, review the script before running it.
- A hard process crash between SQL operations can leave `Status='STARTED'`. This iteration covers handled exceptions, not process termination or multi-worker coordination.
- This is a local, sequential demo pipeline; it does not support concurrent runs against the same checkpoint directory.
- Tests use simulated API and SQL calls; your local SSMS provides the final integration verification.
