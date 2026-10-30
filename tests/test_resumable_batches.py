"""No real Gemini or SQL Server calls: checkpoint regression tests."""
import json
from types import SimpleNamespace

import pytest

from models.planner_schemas import PresentationPlanSchema
from services.resumable_batch_service import (
    CheckpointError,
    generate_content_resumable,
)


TOPIC = "Compliance i Business Intelligence"


def make_plan(count=9, topic=TOPIC):
    return PresentationPlanSchema.model_validate({
        "topic": topic,
        "presentation_type": "academic",
        "slides_count": count,
        "sections": [{
            "section_number": 1,
            "title": "Wprowadzenie",
            "goal": "Przedstawienie zagadnienia",
        }],
        "slides": [{
            "slide_number": i,
            "section_number": 1,
            "title": f"Zagadnienie {i}",
            "layout": "title_content",
            "objective": f"Omówienie zagadnienia {i}",
            "content_brief": ["Wyjaśnij pojęcie"],
        } for i in range(1, count + 1)],
    })


def make_batch_payload(plan, first, last):
    slides = plan.slides[first - 1:last]
    return {
        "title": "Zarządzanie zgodnością — prezentacja",
        "topic": plan.topic,
        "language": "pl",
        "slides_count": len(slides),
        "slides": [{
            "slide_number": local_number,
            "layout": s.layout.value,
            "title": s.title,
            "speaker_notes": "Notatka",
            "bullet_points": ["Testowy punkt"],
        } for local_number, s in enumerate(slides, start=1)],
    }


class FakeClient:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = 0
        self.models = self

    def generate_content(self, **kwargs):
        self.calls += 1
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text=json.dumps(outcome, ensure_ascii=False))


def test_resumes_after_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setenv("GEMINI_THINKING_LEVEL", "medium")
    plan = make_plan(9)
    root = tmp_path / "checkpoints"

    first_run = FakeClient([
        make_batch_payload(plan, 1, 4),
        RuntimeError("Simulated HTTP 503"),
    ])
    with pytest.raises(RuntimeError, match="503"):
        generate_content_resumable(
            plan, batch_size=4, checkpoint_root=root, client=first_run,
        )
    assert first_run.calls == 2
    assert len(list(root.glob("*/batch_001.json"))) == 1
    assert not list(root.glob("*/batch_002.json"))

    second_run = FakeClient([
        make_batch_payload(plan, 5, 8),
        make_batch_payload(plan, 9, 9),
    ])
    result = generate_content_resumable(
        plan, batch_size=4, checkpoint_root=root, client=second_run,
    )
    assert second_run.calls == 2  # batch 1 read from disk, not Gemini
    assert [s.slide_number for s in result.slides] == list(range(1, 10))
    assert len(result.slides) == 9

    # A complete cache requires zero API requests.
    no_api = FakeClient([])
    result_again = generate_content_resumable(
        plan, batch_size=4, checkpoint_root=root, client=no_api,
    )
    assert no_api.calls == 0
    assert result_again.slides_count == 9


def test_changed_plan_does_not_use_old_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    plan_a = make_plan(4, "Temat A")
    plan_b = make_plan(4, "Temat B")
    root = tmp_path / "checkpoints"

    generate_content_resumable(
        plan_a, checkpoint_root=root,
        client=FakeClient([make_batch_payload(plan_a, 1, 4)]),
    )
    second_client = FakeClient([make_batch_payload(plan_b, 1, 4)])
    generate_content_resumable(
        plan_b, checkpoint_root=root, client=second_client,
    )
    assert second_client.calls == 1
    assert len(list(root.glob("*/batch_001.json"))) == 2


def test_changed_model_does_not_use_old_cache(monkeypatch, tmp_path):
    plan = make_plan(4)
    root = tmp_path / "checkpoints"
    monkeypatch.setenv("GEMINI_MODEL", "test-model-a")
    generate_content_resumable(
        plan, checkpoint_root=root,
        client=FakeClient([make_batch_payload(plan, 1, 4)]),
    )
    monkeypatch.setenv("GEMINI_MODEL", "test-model-b")
    other = FakeClient([make_batch_payload(plan, 1, 4)])
    generate_content_resumable(plan, checkpoint_root=root, client=other)
    assert other.calls == 1


def test_corrupt_checkpoint_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    plan = make_plan(4)
    root = tmp_path / "checkpoints"
    generate_content_resumable(
        plan, checkpoint_root=root,
        client=FakeClient([make_batch_payload(plan, 1, 4)]),
    )
    file_path = next(root.glob("*/batch_001.json"))
    content = json.loads(file_path.read_text(encoding="utf-8"))
    content["presentation"]["slides"][0]["title"] = "Zmieniony tytuł"
    file_path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")

    no_api = FakeClient([])
    with pytest.raises(CheckpointError, match="sumę kontrolną"):
        generate_content_resumable(plan, checkpoint_root=root, client=no_api)
    assert no_api.calls == 0


def test_different_batch_size_uses_separate_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    plan = make_plan(4)
    root = tmp_path / "checkpoints"
    generate_content_resumable(
        plan, batch_size=4, checkpoint_root=root,
        client=FakeClient([make_batch_payload(plan, 1, 4)]),
    )
    other = FakeClient([
        make_batch_payload(plan, 1, 2),
        make_batch_payload(plan, 3, 4),
    ])
    generate_content_resumable(
        plan, batch_size=2, checkpoint_root=root, client=other,
    )
    assert other.calls == 2
