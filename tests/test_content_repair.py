
"""Offline tests for Planned Generation Content Repair."""

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from models.planner_schemas import PresentationPlanSchema
from services.batch_content_service import (
    validate_or_repair_batch_response,
)
from services.resumable_batch_service import generate_content_resumable


TOPIC = "Compliance i Business Intelligence"
SLIDE_TITLE = "Analiza przypadku"


def make_payload(solution):
    return {
        "title": "Prezentacja o compliance",
        "topic": TOPIC,
        "language": "pl",
        "slides_count": 1,
        "slides": [{
            "slide_number": 1,
            "layout": "case_study",
            "title": SLIDE_TITLE,
            "problem": "Nieefektywna kontrola zgodności.",
            "analysis": "Rozproszone dane utrudniają analizę.",
            "solution": solution,
            "outcome": "Usprawnienie monitorowania ryzyk.",
        }],
    }


def make_json(solution):
    return json.dumps(make_payload(solution), ensure_ascii=False)


def make_plan():
    return PresentationPlanSchema.model_validate({
        "topic": TOPIC,
        "presentation_type": "academic",
        "slides_count": 1,
        "sections": [{
            "section_number": 1,
            "title": "Analiza",
            "goal": "Analiza przykładowego przypadku",
        }],
        "slides": [{
            "slide_number": 1,
            "section_number": 1,
            "title": SLIDE_TITLE,
            "layout": "case_study",
            "objective": "Analiza wdrożenia BI",
            "content_brief": ["Problem i rozwiązanie"],
        }],
    })


class FakeGemini:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []
        self.models = self

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text=next(self.responses))


INVALID = make_json("A" * 200)
VALID = make_json("Wdrożono dashboard BI do analizy ryzyk.")


def test_valid_response_needs_no_repair():
    client = FakeGemini([])

    result = validate_or_repair_batch_response(
        VALID,
        client=client,
        model_name="test-model",
        config=None,
    )

    assert result.slides_count == 1
    assert len(client.calls) == 0


def test_invalid_response_repaired_once():
    client = FakeGemini([VALID])

    result = validate_or_repair_batch_response(
        INVALID,
        client=client,
        model_name="test-model",
        config=None,
    )

    assert len(client.calls) == 1
    assert len(result.slides[0].solution) <= 170
    assert result.slides[0].title == SLIDE_TITLE
    assert result.slides[0].problem == (
        "Nieefektywna kontrola zgodności."
    )

    repair_prompt = client.calls[0]["contents"]
    assert "slides.0.case_study.solution" in repair_prompt


def test_failed_repair_does_not_loop():
    client = FakeGemini([INVALID])

    with pytest.raises(ValidationError):
        validate_or_repair_batch_response(
            INVALID,
            client=client,
            model_name="test-model",
            config=None,
        )

    assert len(client.calls) == 1


def test_repaired_batch_is_checkpointed(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setenv("GEMINI_THINKING_LEVEL", "medium")

    plan = make_plan()
    client = FakeGemini([INVALID, VALID])

    result = generate_content_resumable(
        plan,
        batch_size=1,
        checkpoint_root=tmp_path,
        client=client,
    )

    assert result.slides_count == 1
    assert len(client.calls) == 2

    checkpoints = list(tmp_path.glob("*/batch_001.json"))
    assert len(checkpoints) == 1

    cached_client = FakeGemini([])

    cached_result = generate_content_resumable(
        plan,
        batch_size=1,
        checkpoint_root=tmp_path,
        client=cached_client,
    )

    assert cached_result.slides_count == 1
    assert len(cached_client.calls) == 0
