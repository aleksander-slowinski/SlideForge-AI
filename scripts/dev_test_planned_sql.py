"""Write one clearly marked TEST failed Planned run to real SQL, no Gemini calls.

Run only after applying sql/planned_telemetry.sql; uses existing local .env.
"""
from services import telemetry_service
from services.planned_telemetry_service import (
    start_planned_run,
    record_batch,
    save_planned_counts,
)


def main():
    run_id = start_planned_run(
        topic='[TEST] Planned telemetry (synthetic 503)',
        slides_count=12,
        fingerprint='0' * 64,
        batch_size=4,
    )
    try:
        record_batch(
            run_id=run_id,
            batch_index=1, slide_from=1, slide_to=4,
            outcome='FAILED', duration_ms=9900, api_calls=3,
            llm_duration_ms=5200,
            prompt_tokens=None, output_tokens=None,
            thinking_tokens=None, total_tokens=None,
            last_http_status=503,
        )
        save_planned_counts(
            run_id=run_id, api_call_count=3, checkpoint_hit_count=0,
        )
        telemetry_service.fail_generation(
            run_id=run_id, duration_ms=10000, error_code='503',
        )
    except Exception:
        # Do not leave a synthetic STARTED record after a test error if possible.
        try:
            telemetry_service.fail_generation(
                run_id=run_id, duration_ms=0, error_code='SQL_TEST_FAILED',
            )
        except Exception:
            pass
        raise
    print(f'Zapisano syntetyczną próbę Planned: RunID={run_id} (FAILED/503)')


if __name__ == '__main__':
    main()
