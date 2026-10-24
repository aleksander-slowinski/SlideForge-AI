
import pytest

from pptx import Presentation as PptxPresentation

from services import (
    presentation_service,
    telemetry_service,
)

from services.generation_tracking_service import (
    build_tracked_presentation,
)


def unavailable_database(**kwargs):
    raise ConnectionError(
        "Simulated SQL Server outage"
    )


def test_demo_survives_sql_connection_failure(
    monkeypatch,
    tmp_path,
):
    """
    Brak połączenia z SQL Server
    nie może blokować prezentacji.
    """

    monkeypatch.setattr(
        telemetry_service,
        "start_generation",
        unavailable_database,
    )

    output = tmp_path / "demo_no_sql.pptx"

    result = build_tracked_presentation(
        mode="demo",
        topic="Release test",
        slides_count=4,
        output_path=str(output),
    )

    assert output.exists()
    assert output.stat().st_size > 0

    assert result.slides_count == 4

    pptx = PptxPresentation(str(output))

    # 4 slajdy treści + slajd tytułowy.
    assert len(pptx.slides) == 5


def test_demo_survives_sql_finish_failure(
    monkeypatch,
    tmp_path,
):
    """
    Awaria zapisu SUCCESS nie może
    unieważnić gotowego pliku PPTX.
    """

    monkeypatch.setattr(
        telemetry_service,
        "start_generation",
        lambda **kwargs: 999001,
    )

    monkeypatch.setattr(
        telemetry_service,
        "finish_generation",
        unavailable_database,
    )

    saved_quality = []

    monkeypatch.setattr(
        telemetry_service,
        "save_quality_report",
        lambda **kwargs: saved_quality.append(
            kwargs
        ),
    )

    output = tmp_path / "demo_finish_error.pptx"

    result = build_tracked_presentation(
        mode="demo",
        topic="Release test",
        slides_count=4,
        output_path=str(output),
    )

    assert result.slides_count == 4
    assert output.exists()

    # Gdy nie zapisano SUCCESS,
    # nie zapisujemy osieroconego raportu.
    assert saved_quality == []


def test_gemini_failure_is_logged(
    monkeypatch,
    tmp_path,
):
    """
    Awaria generowania powinna zostać
    oznaczona statusem FAILED.
    """

    failed_calls = []

    monkeypatch.setattr(
        telemetry_service,
        "start_generation",
        lambda **kwargs: 999002,
    )

    monkeypatch.setattr(
        telemetry_service,
        "fail_generation",
        lambda **kwargs: failed_calls.append(
            kwargs
        ),
    )

    monkeypatch.setattr(
        telemetry_service,
        "save_run_metrics",
        lambda **kwargs: None,
    )

    def fake_gemini_failure(**kwargs):
        raise RuntimeError(
            "Simulated Gemini failure"
        )

    monkeypatch.setattr(
        presentation_service,
        "build_presentation",
        fake_gemini_failure,
    )

    output = tmp_path / "failed_gemini.pptx"

    with pytest.raises(
        RuntimeError,
        match="Simulated Gemini failure",
    ):
        build_tracked_presentation(
            mode="gemini",
            topic="Release test",
            slides_count=4,
            output_path=str(output),
        )

    assert len(failed_calls) == 1

    assert failed_calls[0]["run_id"] == 999002
    assert (
        failed_calls[0]["error_code"]
        == "RuntimeError"
    )

    assert not output.exists()
