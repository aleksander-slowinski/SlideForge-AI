
from services import telemetry_service

from services.generation_tracking_service import (
    build_tracked_presentation,
)

from services.quality_v2_service import QualityReport


def test_quality_is_saved_after_success(
    monkeypatch, tmp_path
):
    events = []

    monkeypatch.setattr(
        telemetry_service,
        "start_generation",
        lambda **kwargs: 901,
    )

    def fake_finish(**kwargs):
        events.append("SUCCESS")

    def fake_save(**kwargs):
        events.append("QUALITY")

        assert kwargs["run_id"] == 901
        assert isinstance(
            kwargs["report"], QualityReport
        )
        assert 0 <= kwargs["report"].score <= 100

    monkeypatch.setattr(
        telemetry_service,
        "finish_generation",
        fake_finish,
    )

    monkeypatch.setattr(
        telemetry_service,
        "save_quality_report",
        fake_save,
    )

    output = tmp_path / "quality_success.pptx"

    build_tracked_presentation(
        mode="demo",
        topic="",
        slides_count=4,
        output_path=str(output),
    )

    assert output.exists()
    assert events == ["SUCCESS", "QUALITY"]


def test_quality_storage_failure_does_not_block(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        telemetry_service,
        "start_generation",
        lambda **kwargs: 902,
    )

    monkeypatch.setattr(
        telemetry_service,
        "finish_generation",
        lambda **kwargs: None,
    )

    def broken_quality_storage(**kwargs):
        raise ConnectionError("SQL Server unavailable")

    monkeypatch.setattr(
        telemetry_service,
        "save_quality_report",
        broken_quality_storage,
    )

    output = tmp_path / "quality_offline.pptx"

    presentation = build_tracked_presentation(
        mode="demo",
        topic="",
        slides_count=4,
        output_path=str(output),
    )

    assert output.exists()
    assert presentation.slides_count == 4


def test_quality_not_saved_when_finish_fails(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        telemetry_service,
        "start_generation",
        lambda **kwargs: 903,
    )

    def broken_finish(**kwargs):
        raise ConnectionError("SQL Server unavailable")

    monkeypatch.setattr(
        telemetry_service,
        "finish_generation",
        broken_finish,
    )

    saved = []

    monkeypatch.setattr(
        telemetry_service,
        "save_quality_report",
        lambda **kwargs: saved.append(kwargs),
    )

    output = tmp_path / "unfinished_run.pptx"

    presentation = build_tracked_presentation(
        mode="demo",
        topic="",
        slides_count=4,
        output_path=str(output),
    )

    assert output.exists()
    assert presentation.slides_count == 4
    assert saved == []
