from copy import deepcopy

import pytest
from pydantic import ValidationError
from pptx import Presentation

from models.schemas import (
    PresentationSchema,
    ComparisonSlide,
)
from services.ppt_service import create_presentation
from services.quality_service import analyze_presentation
from pptx.enum.text import MSO_AUTO_SIZE

@pytest.fixture
def valid_data():
    return {
        "title": "Test SlideForge",
        "topic": "Test automatyczny",
        "language": "pl",
        "slides_count": 4,
        "slides": [
            {
                "slide_number": 1,
                "title": "Slajd tekstowy",
                "layout": "title_content",
                "bullet_points": ["Punkt pierwszy"],
                "speaker_notes": "Notatki pierwszego slajdu",
            },
            {
                "slide_number": 2,
                "title": "Dwie kolumny",
                "layout": "two_columns",
                "columns": [
                    {
                        "title": "Lewa",
                        "bullet_points": ["Punkt A"],
                    },
                    {
                        "title": "Prawa",
                        "bullet_points": ["Punkt B"],
                    },
                ],
            },
            {
                "slide_number": 3,
                "title": "Porównanie rozwiązań",
                "layout": "comparison",
                "items": [
                    {
                        "title": "Rozwiązanie A",
                        "bullet_points": ["Cecha A"],
                    },
                    {
                        "title": "Rozwiązanie B",
                        "bullet_points": ["Cecha B"],
                    },
                ],
            },
            {
                "slide_number": 4,
                "title": "Podsumowanie prezentacji",
                "layout": "conclusion",
                "key_points": ["Najważniejszy wniosek"],
            },
        ],
    }


def test_valid_presentation(valid_data):
    result = PresentationSchema.model_validate(valid_data)

    assert result.slides_count == 4
    assert len(result.slides) == 4
    assert isinstance(result.slides[2], ComparisonSlide)


def test_invalid_slides_count(valid_data):
    data = deepcopy(valid_data)
    data["slides_count"] = 5

    with pytest.raises(ValidationError):
        PresentationSchema.model_validate(data)


def test_invalid_slide_number(valid_data):
    data = deepcopy(valid_data)
    data["slides"][2]["slide_number"] = 8

    with pytest.raises(ValidationError):
        PresentationSchema.model_validate(data)


def test_invalid_layout(valid_data):
    data = deepcopy(valid_data)
    data["slides"][0]["layout"] = "unknown_layout"

    with pytest.raises(ValidationError):
        PresentationSchema.model_validate(data)


def test_invalid_columns(valid_data):
    data = deepcopy(valid_data)
    data["slides"][1]["columns"].append(
        {"title": "Trzecia", "bullet_points": ["Punkt C"]}
    )

    with pytest.raises(ValidationError):
        PresentationSchema.model_validate(data)


def test_pptx_generation(valid_data, tmp_path):
    presentation = PresentationSchema.model_validate(valid_data)

    output_file = tmp_path / "test_slideforge.pptx"

    create_presentation(presentation, str(output_file))

    assert output_file.exists()

    generated = Presentation(str(output_file))

    # 1 tytułowy + 4 merytoryczne
    assert len(generated.slides) == 5

    assert generated.slides[0].shapes.title.text == "Test SlideForge"
    assert generated.slides[1].shapes.title.text == "Slajd tekstowy"
    assert generated.slides[3].shapes.title.text == "Porównanie rozwiązań"

    assert (
        "Notatki pierwszego slajdu"
        in generated.slides[1].notes_slide.notes_text_frame.text
    )
    
def test_quality_valid(valid_data):
    presentation = PresentationSchema.model_validate(valid_data)

    warnings = analyze_presentation(presentation)

    assert warnings == []


def test_quality_long_bullet(valid_data):
    data = deepcopy(valid_data)

    data["slides"][0]["bullet_points"] = [
        "A" * 150
    ]

    presentation = PresentationSchema.model_validate(data)

    warnings = analyze_presentation(presentation)

    assert len(warnings) > 0
    assert "110 znaków" in warnings[0]

    

def test_column_formatting(valid_data, tmp_path):
    presentation = PresentationSchema.model_validate(valid_data)
    output_file = tmp_path / "formatting_test.pptx"

    create_presentation(presentation, str(output_file))
    generated = Presentation(str(output_file))

    # ==========================================
    # SLAJD 3: TWO_COLUMNS
    # ==========================================

    two_columns = generated.slides[2]

    left = two_columns.placeholders[1].text_frame
    right = two_columns.placeholders[2].text_frame

    # Lewa kolumna
    assert left.paragraphs[0].text == "Lewa"
    assert "Punkt A" in left.text
    assert left.paragraphs[0].font.bold is True
    assert left.paragraphs[0]._p.xpath("./a:pPr/a:buNone")
    assert left.word_wrap is True
    assert left.auto_size == MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE

    # Prawa kolumna
    assert right.paragraphs[0].text == "Prawa"
    assert "Punkt B" in right.text
    assert right.paragraphs[0].font.bold is True
    assert right.paragraphs[0]._p.xpath("./a:pPr/a:buNone")
    assert right.word_wrap is True
    assert right.auto_size == MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE

 
    # SLAJD 4: COMPARISON

    comparison = generated.slides[3]

    tables = [
        shape.table
        for shape in comparison.shapes
        if shape.has_table
    ]

    assert len(tables) == 1

    table = tables[0]

    assert len(table.columns) == 2

    assert table.cell(0, 0).text == "Rozwiązanie A"
    assert table.cell(0, 1).text == "Rozwiązanie B"

    assert "Cecha A" in table.cell(1, 0).text
    assert "Cecha B" in table.cell(1, 1).text

    assert table.cell(0, 0).text_frame.paragraphs[0].font.bold is True
    assert table.cell(0, 1).text_frame.paragraphs[0].font.bold is True

    # Porównanie nie powinno zawierać pustych
    # placeholderów po układzie dwukolumnowym
    remaining_placeholders = [
        shape.placeholder_format.idx
        for shape in comparison.shapes
        if shape.is_placeholder
    ]

    assert 1 not in remaining_placeholders
    assert 2 not in remaining_placeholders

    
def test_conclusion_cards(valid_data, tmp_path):
    presentation = PresentationSchema.model_validate(valid_data)
    output_file = tmp_path / "conclusion_test.pptx"

    create_presentation(presentation, str(output_file))
    generated = Presentation(str(output_file))

    # Slajd 5: podsumowanie
    conclusion = generated.slides[4]

    assert conclusion.shapes.title.text == "Podsumowanie prezentacji"

    # Sprawdzamy obecność numeru i treści wniosku
    texts = [
        shape.text
        for shape in conclusion.shapes
        if shape.has_text_frame
    ]

    assert "01" in texts
    assert "Najważniejszy wniosek" in texts

    # Nie powinien pozostać placeholder zawartości
    remaining_placeholders = [
        shape.placeholder_format.idx
        for shape in conclusion.shapes
        if shape.is_placeholder
    ]

    assert 1 not in remaining_placeholders

    
def test_demo_mode(tmp_path):
    from services.demo_service import build_demo_presentation

    output_file = tmp_path / "demo_test.pptx"

    presentation = build_demo_presentation(
        output_path=str(output_file)
    )

    assert presentation.slides_count == 4
    assert output_file.exists()

    generated = Presentation(str(output_file))

    assert len(generated.slides) == 5
    assert generated.slides[0].shapes.title.text == (
        "SlideForge AI — Demonstracja"
    )

    assert any(
        shape.has_table
        for shape in generated.slides[3].shapes
    )
