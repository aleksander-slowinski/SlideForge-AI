"""Offline tests for the Planned Generation Streamlit backend."""
from types import SimpleNamespace

import pytest
from pptx import Presentation as PptxPresentation

from models.planner_schemas import PresentationPlanSchema
from models.schemas import PresentationSchema
from services.planned_presentation_service import (
    build_planned_artifact,
    checkpoint_overview,
    load_presentation_plan,
)


def sample_plan():
    return PresentationPlanSchema.model_validate({
        "topic": "Business Intelligence i compliance",
        "presentation_type": "academic",
        "slides_count": 2,
        "sections": [{"section_number": 1, "title": "Wprowadzenie", "goal": "Wstęp do tematu"}],
        "slides": [
            {"slide_number": i, "section_number": 1,
             "title": f"Zagadnienie {i}", "layout": "title_content",
             "objective": "Wyjaśnienie zagadnienia", "content_brief": ["Definicja"]}
            for i in (1, 2)
        ],
    })


def sample_presentation(plan):
    return PresentationSchema.model_validate({
        "title": "Prezentacja testowa",
        "topic": plan.topic, "language": "pl", "slides_count": 2,
        "slides": [
            {"slide_number": i, "title": f"Zagadnienie {i}",
             "layout": "title_content", "speaker_notes": "Test",
             "bullet_points": ["Ważny punkt"]}
            for i in (1, 2)
        ],
    })


def fake_renderer(data, filename):
    pptx = PptxPresentation()
    for _ in range(data.slides_count + 1):
        pptx.slides.add_slide(pptx.slide_layouts[6])
    pptx.save(filename)


def fake_report(_presentation):
    return SimpleNamespace(score=96, warning_count=1, error_count=0)


def test_load_json_plan():
    plan = sample_plan()
    loaded = load_presentation_plan(plan.model_dump_json().encode("utf-8"))
    assert loaded.slides_count == 2


def test_empty_checkpoint_overview(tmp_path):
    fingerprint, rows = checkpoint_overview(
        sample_plan(), checkpoint_root=tmp_path, batch_size=1,
    )
    assert len(fingerprint) == 64
    assert [r["Status"] for r in rows] == ["Do wygenerowania"] * 2


def test_build_artifact_without_api(tmp_path):
    plan = sample_plan()
    calls = []

    def fake_generator(**kwargs):
        calls.append(kwargs)
        return sample_presentation(plan)

    artifact = build_planned_artifact(
        plan, output_dir=tmp_path / "output", checkpoint_root=tmp_path / "checkpoints",
        generate_fn=fake_generator, render_fn=fake_renderer, evaluate_fn=fake_report,
    )
    assert len(calls) == 1
    assert artifact.slide_count == 2
    assert artifact.quality_report.score == 96
    assert len(artifact.pptx_data) > 500
    assert (tmp_path / "output" / artifact.filename).exists()


def test_reject_wrong_slide_title(tmp_path):
    plan = sample_plan()
    broken = sample_presentation(plan)
    broken.slides[0].title = "Inny tytuł"

    with pytest.raises(ValueError, match="Niezgodność z planem"):
        build_planned_artifact(
            plan, output_dir=tmp_path / "output", checkpoint_root=tmp_path / "checkpoints",
            generate_fn=lambda **kwargs: broken,
            render_fn=fake_renderer, evaluate_fn=fake_report,
        )


def test_invalid_pptx_not_published(tmp_path):
    plan = sample_plan()
    def corrupt_renderer(data, filename):
        from pathlib import Path
        Path(filename).write_bytes(b"not a PowerPoint")

    with pytest.raises(Exception):
        build_planned_artifact(
            plan, output_dir=tmp_path / "output", checkpoint_root=tmp_path / "checkpoints",
            generate_fn=lambda **kwargs: sample_presentation(plan),
            render_fn=corrupt_renderer, evaluate_fn=fake_report,
        )
    assert list((tmp_path / "output").glob("*.pptx")) == []


def test_failed_generation_does_not_publish(tmp_path):
    plan = sample_plan()
    def fail(**kwargs):
        raise RuntimeError("simulated 503")

    with pytest.raises(RuntimeError):
        build_planned_artifact(
            plan, output_dir=tmp_path / "output", checkpoint_root=tmp_path / "checkpoints",
            generate_fn=fail, render_fn=fake_renderer, evaluate_fn=fake_report,
        )
    assert not (tmp_path / "output").exists()
