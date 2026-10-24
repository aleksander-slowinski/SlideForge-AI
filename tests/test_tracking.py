
import pytest

from services import telemetry_service
from services.generation_tracking_service import (
    build_tracked_presentation,
)


def test_tracked_demo_success(monkeypatch, tmp_path):
    """Udane generowanie zapisuje STARTED i SUCCESS."""

    events = []

    def fake_start(**kwargs):
        events.append(("STARTED", kwargs))
        return 123

    def fake_finish(**kwargs):
        events.append(("SUCCESS", kwargs))

    monkeypatch.setattr(
        telemetry_service, "start_generation", fake_start
    )

    monkeypatch.setattr(
        telemetry_service, "finish_generation", fake_finish
    )

    monkeypatch.setattr(
    telemetry_service, "save_quality_report",
    lambda **kwargs: None,
)

    output_file = tmp_path / "tracked_demo.pptx"

    presentation = build_tracked_presentation(
        mode="demo",
        topic="",
        slides_count=10,
        output_path=str(output_file),
    )

    assert output_file.exists()
    assert presentation.slides_count == 4

    assert events[0][0] == "STARTED"
    assert events[0][1]["mode"] == "demo"
    assert events[0][1]["requested_slides"] == 4

    assert events[1][0] == "SUCCESS"
    assert events[1][1]["run_id"] == 123


def test_generation_failure_is_logged(
    monkeypatch, tmp_path
):
    """Awaria generatora zapisuje FAILED."""

    from services import demo_service

    events = []

    monkeypatch.setattr(
        telemetry_service,
        "start_generation",
        lambda **kwargs: 456,
    )

    def broken_generator(**kwargs):
        raise RuntimeError("Symulowana awaria")

    monkeypatch.setattr(
        demo_service,
        "build_demo_presentation",
        broken_generator,
    )

    def fake_fail(**kwargs):
        events.append(kwargs)

    monkeypatch.setattr(
        telemetry_service,
        "fail_generation",
        fake_fail,
    )

    with pytest.raises(
        RuntimeError, match="Symulowana awaria"
    ):
        build_tracked_presentation(
            mode="demo",
            topic="Test",
            slides_count=4,
            output_path=str(tmp_path / "error.pptx"),
        )

    assert len(events) == 1
    assert events[0]["run_id"] == 456
    assert events[0]["error_code"] == "RuntimeError"


def test_database_failure_does_not_stop_demo(
    monkeypatch, tmp_path
):
    """Brak SQL Server nie blokuje generatora."""

    def broken_database(**kwargs):
        raise ConnectionError("Baza niedostępna")

    monkeypatch.setattr(
        telemetry_service,
        "start_generation",
        broken_database,
    )

    output_file = tmp_path / "offline_demo.pptx"

    presentation = build_tracked_presentation(
        mode="demo",
        topic="",
        slides_count=4,
        output_path=str(output_file),
    )

    assert output_file.exists()
    assert presentation.slides_count == 4
