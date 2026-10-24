
import pytest

from pptx import Presentation

from models.schemas import PresentationSchema
from services.ppt_service import create_presentation


CASES = [
    {
        "slide_number": 1,
        "layout": "section_divider",
        "title": "Analiza ryzyka",
        "subtitle": "Rozdział II",
        "speaker_notes": "Wprowadzenie do sekcji.",
    },
    {
        "slide_number": 1,
        "layout": "process_flow",
        "title": "Proces audytu",
        "steps": [
            {
                "heading": "Planowanie",
                "description": "Określenie zakresu audytu.",
            },
            {
                "heading": "Analiza",
                "description": "Weryfikacja zgromadzonych danych.",
            },
            {
                "heading": "Raportowanie",
                "description": "Przedstawienie wyników.",
            },
        ],
        "speaker_notes": "Omów etapy procesu.",
    },
    {
        "slide_number": 1,
        "layout": "timeline",
        "title": "Harmonogram projektu",
        "events": [
            {
                "period": "Q1",
                "heading": "Analiza",
                "description": "Identyfikacja wymagań.",
            },
            {
                "period": "Q2",
                "heading": "Wdrożenie",
                "description": "Implementacja rozwiązania.",
            },
            {
                "period": "Q3",
                "heading": "Ewaluacja",
                "description": "Ocena rezultatów.",
            },
        ],
        "speaker_notes": "Omów harmonogram.",
    },
]


@pytest.mark.parametrize(
    "slide_data",
    CASES,
    ids=["section_divider", "process_flow", "timeline"],
)
def test_advanced_layout_generation(slide_data, tmp_path):

    data = PresentationSchema.model_validate({
        "title": "Test zaawansowanych layoutów",
        "topic": "Test",
        "language": "pl",
        "slides_count": 1,
        "slides": [slide_data],
    })

    output_file = (
        tmp_path / f"{slide_data['layout']}.pptx"
    )

    create_presentation(
        data=data,
        filename=str(output_file),
    )

    assert output_file.exists()

    prs = Presentation(str(output_file))

    # Slajd tytułowy + jeden merytoryczny
    assert len(prs.slides) == 2

    content_slide = prs.slides[1]

    all_text = " ".join(
        shape.text
        for shape in content_slide.shapes
        if shape.has_text_frame
    )

    assert slide_data["title"] in all_text

    notes = content_slide.notes_slide.notes_text_frame.text

    assert slide_data["speaker_notes"] in notes