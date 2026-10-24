
import json

from types import SimpleNamespace

import pytest

from models.planner_schemas import PresentationPlanSchema
from services.batch_content_service import (
    split_plan_into_batches,
    generate_content_from_plan,
)


TOPIC = "Prawo i analiza danych"


def make_plan(count=9):
    return PresentationPlanSchema.model_validate(
        {
            "topic": TOPIC,
            "presentation_type": "academic",
            "slides_count": count,
            "sections": [
                {
                    "section_number": 1,
                    "title": "Rozdział testowy",
                    "goal": "Przedstawienie zagadnienia",
                }
            ],
            "slides": [
                {
                    "slide_number": i,
                    "section_number": 1,
                    "title": f"Slajd numer {i}",
                    "layout": "title_content",
                    "objective": (
                        "Omówienie wybranego zagadnienia"
                    ),
                    "content_brief": [
                        "Wyjaśnij definicję",
                    ],
                }
                for i in range(1, count + 1)
            ],
        }
    )


def make_response(plan, batch):
    return {
        "title": "Prezentacja testowa",
        "topic": plan.topic,
        "language": "pl",
        "slides_count": len(batch),
        "slides": [
            {
                "slide_number": local_number,
                "title": slide.title,
                "layout": slide.layout.value,
                "speaker_notes": "Notatki prelegenta",
                "bullet_points": [
                    "Przykładowy punkt prezentacji"
                ],
            }
            for local_number, slide in enumerate(
                batch, start=1
            )
        ],
    }


class FakeClient:
    def __init__(self, payloads):
        self.responses = iter(payloads)
        self.models = self
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)

        return SimpleNamespace(
            text=json.dumps(
                next(self.responses),
                ensure_ascii=False,
            )
        )


def test_batch_split():
    plan = make_plan(9)

    batches = split_plan_into_batches(
        plan, batch_size=4
    )

    assert [len(batch) for batch in batches] == [
        4, 4, 1
    ]


def test_batch_split_25_slides():
    plan = make_plan(25)

    batches = split_plan_into_batches(
        plan, batch_size=4
    )

    assert [len(batch) for batch in batches] == [
        4, 4, 4, 4, 4, 4, 1
    ]


def test_merged_presentation():
    plan = make_plan(9)

    payloads = [
        make_response(plan, batch)
        for batch in split_plan_into_batches(plan)
    ]

    client = FakeClient(payloads)

    result = generate_content_from_plan(
        plan=plan,
        batch_size=4,
        client=client,
    )

    assert result.slides_count == 9
    assert len(result.slides) == 9

    assert [
        slide.slide_number
        for slide in result.slides
    ] == list(range(1, 10))

    assert len(client.calls) == 3

    # Nie wysyłamy skomplikowanego
    # Pydantic response_schema do API.
    for call in client.calls:
        config_dict = call["config"].model_dump(
            exclude_none=True
        )

        assert "response_schema" not in config_dict


def test_incorrect_slide_title():
    plan = make_plan(4)

    payload = make_response(
        plan, plan.slides
    )

    payload["slides"][0]["title"] = (
        "Niepoprawny tytuł"
    )

    client = FakeClient([payload])

    with pytest.raises(
        ValueError,
        match="Niezgodny tytuł",
    ):
        generate_content_from_plan(
            plan=plan,
            client=client,
        )


def test_incorrect_layout():
    plan = make_plan(4)

    payload = make_response(
        plan, plan.slides
    )

    payload["slides"][0] = {
        "slide_number": 1,
        "title": plan.slides[0].title,
        "layout": "two_columns",
        "columns": [
            {
                "title": "Kolumna A",
                "bullet_points": ["Punkt A"],
            },
            {
                "title": "Kolumna B",
                "bullet_points": ["Punkt B"],
            },
        ],
    }

    client = FakeClient([payload])

    with pytest.raises(
        ValueError,
        match="Niezgodny layout",
    ):
        generate_content_from_plan(
            plan=plan,
            client=client,
        )


def test_invalid_batch_size():
    plan = make_plan(9)

    with pytest.raises(
        ValueError,
        match="batch_size",
    ):
        split_plan_into_batches(
            plan, batch_size=0
        )
