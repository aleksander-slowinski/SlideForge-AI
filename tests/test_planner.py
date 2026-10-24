
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from models.planner_schemas import PresentationPlanSchema
from services.planner_service import (
    generate_presentation_plan,
)


def make_plan(count=4):
    return {
        "topic": "Business Intelligence i compliance",
        "presentation_type": "academic",
        "slides_count": count,
        "sections": [
            {
                "section_number": 1,
                "title": "Wprowadzenie",
                "goal": "Przedstawienie zagadnienia",
            }
        ],
        "slides": [
            {
                "slide_number": i,
                "section_number": 1,
                "title": f"Zagadnienie {i}",
                "layout": "title_content",
                "objective": f"Omówienie zagadnienia {i}",
                "content_brief": [
                    "Wyjaśnij kluczowe pojęcia",
                    "Przedstaw znaczenie praktyczne",
                ],
            }
            for i in range(1, count + 1)
        ],
    }


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []
        self.models = self

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)

        return SimpleNamespace(
            text=json.dumps(self.payload),
            parsed=None,
        )


def test_valid_plan():
    plan = PresentationPlanSchema.model_validate(
        make_plan()
    )

    assert plan.slides_count == 4
    assert len(plan.slides) == 4
    assert len(plan.sections) == 1


def test_plan_supports_25_slides():
    plan = PresentationPlanSchema.model_validate(
        make_plan(25)
    )

    assert len(plan.slides) == 25
    assert plan.slides[-1].slide_number == 25


def test_incorrect_slide_count():
    payload = make_plan()
    payload["slides_count"] = 5

    with pytest.raises(ValidationError):
        PresentationPlanSchema.model_validate(payload)


def test_invalid_slide_numbering():
    payload = make_plan()
    payload["slides"][2]["slide_number"] = 8

    with pytest.raises(ValidationError):
        PresentationPlanSchema.model_validate(payload)


def test_invalid_section_reference():
    payload = make_plan()
    payload["slides"][1]["section_number"] = 3

    with pytest.raises(ValidationError):
        PresentationPlanSchema.model_validate(payload)


def test_planner_with_mocked_gemini(monkeypatch):
    monkeypatch.setenv(
        "GEMINI_MODEL",
        "gemini-3.8-flash",
    )
    monkeypatch.setenv(
        "GEMINI_THINKING_LEVEL",
        "medium",
    )

    fake_client = FakeClient(make_plan())

    plan = generate_presentation_plan(
        topic="Business Intelligence i compliance",
        slides_count=4,
        presentation_type="academic",
        client=fake_client,
    )

    assert len(plan.slides) == 4
    assert len(fake_client.calls) == 1

    call = fake_client.calls[0]

    assert call["model"] == "gemini-3.8-flash"

    # Wyodrębniamy faktyczną listę
    # dozwolonych layoutów z promptu.
    prompt = call["contents"]

    allowed_section = prompt.split(
        "DOZWOLONE LAYOUTY:", 1
    )[1].split(
        "MATERIAŁY ŹRÓDŁOWE", 1
    )[0].strip()

    allowed_layouts = json.loads(allowed_section)

    assert "title_content" in allowed_layouts

    # Layouty wymagające źródeł są wykluczone
    # z listy, ponieważ ich nie przekazaliśmy.
    assert "key_metrics" not in allowed_layouts
    assert "references" not in allowed_layouts


def test_references_require_sources():
    payload = make_plan()

    payload["slides"][0]["layout"] = "references"

    fake_client = FakeClient(payload)

    with pytest.raises(
        ValueError,
        match="niedozwolonych layoutów",
    ):
        generate_presentation_plan(
            topic="Business Intelligence i compliance",
            slides_count=4,
            client=fake_client,
        )
