
import pytest

from pydantic import ValidationError
from pptx import Presentation

from models.schemas import (
    PresentationSchema,
    KeyMetricsSlide,
    QuoteHighlightSlide,
)
from services.ppt_service import create_presentation


CASES = [
    (
        {
            "slide_number": 1,
            "layout": "key_metrics",
            "title": "Wskaźniki demonstracyjne",
            "metrics": [
                {
                    "label": "Wskaźnik A",
                    "value": "85%",
                    "description": "Przykładowa wartość testowa",
                },
                {
                    "label": "Wskaźnik B",
                    "value": "120",
                    "description": "Przykładowa wartość testowa",
                },
                {
                    "label": "Wskaźnik C",
                    "value": "24 h",
                    "description": "Przykładowa wartość testowa",
                },
                {
                    "label": "Wskaźnik D",
                    "value": "4,5",
                    "description": "Przykładowa wartość testowa",
                },
            ],
            "speaker_notes": "Demonstracja czterech KPI.",
        },
        "85%",
    ),
    (
        {
            "slide_number": 1,
            "layout": "case_study",
            "title": "Hipotetyczne studium przypadku",
            "problem": "Niespójność danych.",
            "analysis": "Identyfikacja przyczyn.",
            "solution": "Wdrożenie walidacji danych.",
            "outcome": "Poprawa spójności informacji.",
            "speaker_notes": "Scenariusz testowy.",
        },
        "Poprawa spójności informacji.",
    ),
    (
        {
            "slide_number": 1,
            "layout": "quote_highlight",
            "title": "Najważniejsza teza",
            "kind": "thesis",
            "statement": (
                "Jakość analiz zależy od jakości "
                "wykorzystanych danych."
            ),
            "speaker_notes": "Omów główną tezę.",
        },
        "Jakość analiz zależy",
    ),
    (
        {
            "slide_number": 1,
            "layout": "references",
            "title": "Źródła testowe",
            "references": [
                {
                    "citation": "Dokument testowy A.",
                    "url": "https://example.com/a",
                },
                {
                    "citation": "Dokument testowy B.",
                    "url": "https://example.com/b",
                },
            ],
            "speaker_notes": "Przykładowe źródła.",
        },
        "Dokument testowy A.",
    ),
]


@pytest.mark.parametrize(
    "slide_data, expected_text",
    CASES,
    ids=[
        "key_metrics",
        "case_study",
        "quote_highlight",
        "references",
    ],
)
def test_academic_layout(
    slide_data, expected_text, tmp_path
):
    data = PresentationSchema.model_validate({
        "title": "SlideForge Academic Layouts",
        "topic": "Test nowych układów",
        "language": "pl",
        "slides_count": 1,
        "slides": [slide_data],
    })

    output = tmp_path / (
        f"{slide_data['layout']}.pptx"
    )

    create_presentation(
        data=data,
        filename=str(output),
    )

    assert output.exists()

    prs = Presentation(str(output))
    assert len(prs.slides) == 2

    slide = prs.slides[1]

    all_text = " ".join(
        shape.text
        for shape in slide.shapes
        if shape.has_text_frame
    )

    assert expected_text in all_text

    notes = slide.notes_slide.notes_text_frame.text
    assert slide_data["speaker_notes"] in notes


def test_metrics_require_at_least_two_values():
    with pytest.raises(ValidationError):
        KeyMetricsSlide.model_validate({
            "slide_number": 1,
            "layout": "key_metrics",
            "title": "Test",
            "metrics": [
                {
                    "label": "KPI",
                    "value": "10",
                }
            ],
        })


def test_direct_quote_requires_attribution():
    with pytest.raises(ValidationError):
        QuoteHighlightSlide.model_validate({
            "slide_number": 1,
            "layout": "quote_highlight",
            "title": "Cytat",
            "kind": "quotation",
            "statement": "Przykładowy cytat testowy.",
        })
