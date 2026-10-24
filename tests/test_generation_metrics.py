
import pytest

from services import (
    demo_service,
    presentation_service,
    telemetry_service,
)

from services.generation_tracking_service import (
    build_tracked_presentation,
)


def test_gemini_metrics_saved(monkeypatch, tmp_path):
    saved = []

    monkeypatch.setattr(
        telemetry_service,
        "start_generation",
        lambda **kwargs: 1001,
    )

    monkeypatch.setattr(
        telemetry_service,
        "finish_generation",
        lambda **kwargs: None,
    )

    monkeypatch.setattr(
        telemetry_service,
        "save_quality_report",
        lambda **kwargs: None,
    )

    def fake_save_metrics(**kwargs):
        saved.append(kwargs)

    monkeypatch.setattr(
        telemetry_service,
        "save_run_metrics",
        fake_save_metrics,
    )

    def fake_gemini(**kwargs):
        metrics = kwargs["metrics"]

        metrics.model_name = "gemini-test"
        metrics.thinking_level = "medium"
        metrics.llm_duration_ms = 1200
        metrics.validation_duration_ms = 5
        metrics.pptx_duration_ms = 150
        metrics.prompt_tokens = 500
        metrics.output_tokens = 800
        metrics.thinking_tokens = 100
        metrics.total_tokens = 1400

        return demo_service.build_demo_presentation(
            output_path=kwargs["output_path"]
        )

    monkeypatch.setattr(
        presentation_service,
        "build_presentation",
        fake_gemini,
    )

    output = tmp_path / "gemini_metrics.pptx"

    build_tracked_presentation(
        mode="gemini",
        topic="Test metryk",
        slides_count=4,
        output_path=str(output),
    )

    assert output.exists()
    assert len(saved) == 1
    assert saved[0]["run_id"] == 1001

    metrics = saved[0]["metrics"]

    assert metrics.model_name == "gemini-test"
    assert metrics.llm_duration_ms == 1200
    assert metrics.prompt_tokens == 500
    assert metrics.total_tokens == 1400


def test_failed_gemini_metrics_saved(
    monkeypatch, tmp_path
):
    saved = []
    failed = []

    monkeypatch.setattr(
        telemetry_service,
        "start_generation",
        lambda **kwargs: 1002,
    )

    monkeypatch.setattr(
        telemetry_service,
        "fail_generation",
        lambda **kwargs: failed.append(kwargs),
    )

    monkeypatch.setattr(
        telemetry_service,
        "save_run_metrics",
        lambda **kwargs: saved.append(kwargs),
    )

    def fake_gemini(**kwargs):
        metrics = kwargs["metrics"]
        metrics.model_name = "gemini-test"
        metrics.llm_duration_ms = 2500

        raise RuntimeError("Gemini error 503")

    monkeypatch.setattr(
        presentation_service,
        "build_presentation",
        fake_gemini,
    )

    with pytest.raises(RuntimeError, match="503"):
        build_tracked_presentation(
            mode="gemini",
            topic="Test błędu",
            slides_count=4,
            output_path=str(tmp_path / "failed.pptx"),
        )

    assert len(failed) == 1
    assert failed[0]["error_code"] == "503"

    assert len(saved) == 1
    assert saved[0]["metrics"].llm_duration_ms == 2500