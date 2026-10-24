
import pytest

from models.schemas import PresentationSchema
from services.quality_v2_service import (
    evaluate_presentation,
    Severity,
)


def make_presentation(slides):
    numbered_slides = [
        {**slide, "slide_number": index}
        for index, slide in enumerate(slides, start=1)
    ]

    return PresentationSchema.model_validate({
        "title": "Quality Engine Test",
        "topic": "Test",
        "language": "pl",
        "slides_count": len(numbered_slides),
        "slides": numbered_slides,
    })


def test_clean_presentation_scores_100():
    data = make_presentation([
        {
            "layout": "title_content",
            "title": "Krótki slajd",
            "bullet_points": [
                "Pierwszy punkt",
                "Drugi punkt",
            ],
        }
    ])

    report = evaluate_presentation(data)

    assert report.score == 100
    assert report.issues == []


def test_two_columns_uses_separate_limits():
    text = "A" * 70

    data = make_presentation([
        {
            "layout": "two_columns",
            "title": "Dwie kolumny",
            "columns": [
                {
                    "title": "Lewa",
                    "bullet_points": [text] * 3,
                },
                {
                    "title": "Prawa",
                    "bullet_points": [text] * 3,
                },
            ],
        }
    ])

    report = evaluate_presentation(data)

    # Ponad 430 znaków na całym slajdzie,
    # ale bez przepełnienia żadnej kolumny.
    assert report.score == 100
    assert report.warning_count == 0


def test_dense_title_content_warning():
    data = make_presentation([
        {
            "layout": "title_content",
            "title": "Obszerny slajd",
            "bullet_points": ["A" * 100] * 5,
        }
    ])

    report = evaluate_presentation(data)

    assert any(
        issue.code == "SLIDE_DENSITY"
        for issue in report.issues
    )

    assert report.score < 100


def test_missing_metric_source():
    data = make_presentation([
        {
            "layout": "key_metrics",
            "title": "KPI",
            "metrics": [
                {
                    "label": "Wskaźnik A",
                    "value": "85%",
                    "description": "Opis",
                },
                {
                    "label": "Wskaźnik B",
                    "value": "120",
                    "description": "Opis",
                    "source": "Dane syntetyczne",
                },
            ],
        }
    ])

    report = evaluate_presentation(data)

    assert report.info_count == 1

    assert any(
        issue.code == "METRIC_SOURCE_MISSING"
        and issue.severity == Severity.INFO
        for issue in report.issues
    )


def test_long_process_step_warning():
    data = make_presentation([
        {
            "layout": "process_flow",
            "title": "Proces",
            "steps": [
                {
                    "heading": "Etap A",
                    "description": "A" * 105,
                },
                {
                    "heading": "Etap B",
                    "description": "Krótki opis",
                },
                {
                    "heading": "Etap C",
                    "description": "Krótki opis",
                },
            ],
        }
    ])

    report = evaluate_presentation(data)

    assert report.warning_count >= 1

    assert any(
        issue.code == "TEXT_TOO_LONG"
        for issue in report.issues
    )


def test_long_quote_warning():
    data = make_presentation([
        {
            "layout": "quote_highlight",
            "title": "Ważna teza",
            "kind": "thesis",
            "statement": "A" * 220,
        }
    ])

    report = evaluate_presentation(data)

    assert report.warning_count == 1
    assert report.score == 94


def test_score_is_comparable_across_lengths():
    def section():
        return {
            "layout": "section_divider",
            "title": "Rozdział",
            "subtitle": "A" * 120,
        }

    short = make_presentation([section()])
    long = make_presentation(
        [section() for _ in range(5)]
    )

    short_report = evaluate_presentation(short)
    long_report = evaluate_presentation(long)

    # Ta sama jakość przeciętnego slajdu
    # powinna dawać ten sam wynik.
    assert short_report.score == long_report.score
    assert short_report.score == 94
