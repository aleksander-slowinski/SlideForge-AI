
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.util import Inches, Pt

from models.schemas import ComparisonSlide


def generate_comparison_slide(
    prs: Presentation,
    data: ComparisonSlide,
):
    # 1. Tworzenie slajdu
    slide = prs.slides.add_slide(prs.slide_layouts[3])
    slide.shapes.title.text = data.title

    # 2. Pobranie geometrii z szablonu
    left = slide.placeholders[1]
    right = slide.placeholders[2]

    x = min(left.left, right.left)
    right_edge = max(
        left.left + left.width,
        right.left + right.width,
    )
    top = min(left.top, right.top)
    height = min(left.height, right.height)

    # 3. Usunięcie niepotrzebnych placeholderów
    for placeholder in (left, right):
        element = placeholder._element
        element.getparent().remove(element)

    # 4. Obliczenie liczby wierszy
    rows = 1 + max(
        len(item.bullet_points)
        for item in data.items
    )

    # 5. Kompaktowa geometria tabeli
    header_height = Inches(0.65)
    preferred_row_height = Inches(0.80)

    available_body_height = height - header_height

    if available_body_height <= 0:
        raise ValueError(
            "Za mało miejsca na tabelę porównawczą."
        )

    body_row_height = min(
        preferred_row_height,
        available_body_height // (rows - 1),
    )

    table_height = (
        header_height + body_row_height * (rows - 1)
    )

    # 6. Tworzenie tabeli
    table = slide.shapes.add_table(
        rows,
        2,
        x,
        top,
        right_edge - x,
        table_height,
    ).table

    table.rows[0].height = header_height

    for row_index in range(1, rows):
        table.rows[row_index].height = body_row_height

    # 7. Wypełnianie kolumn
    for col_index, item in enumerate(data.items):

        # Nagłówki
        cell = table.cell(0, col_index)
        cell.text = item.title

        cell.fill.solid()
        cell.fill.fore_color.rgb = (
            RGBColor(31, 62, 89)
            if col_index == 0
            else RGBColor(56, 93, 121)
        )

        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = Inches(0.16)
        cell.text_frame.word_wrap = True

        paragraph = cell.text_frame.paragraphs[0]
        paragraph.font.bold = True
        paragraph.font.size = Pt(19)
        paragraph.font.color.rgb = RGBColor(255, 255, 255)

        # Wiersze z cechami
        for row_index in range(1, rows):
            cell = table.cell(row_index, col_index)

            point_index = row_index - 1

            cell.text = (
                item.bullet_points[point_index]
                if point_index < len(item.bullet_points)
                else ""
            )

            cell.fill.solid()
            cell.fill.fore_color.rgb = (
                RGBColor(244, 247, 250)
                if row_index % 2
                else RGBColor(233, 239, 246)
            )

            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = Inches(0.16)
            cell.margin_right = Inches(0.12)
            cell.text_frame.word_wrap = True
            cell.text_frame.auto_size = (
                MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            )

            paragraph = cell.text_frame.paragraphs[0]
            paragraph.font.size = Pt(16)
            paragraph.font.color.rgb = RGBColor(38, 48, 60)

    # 8. Notatki prelegenta
    if data.speaker_notes:
        slide.notes_slide.notes_text_frame.text = (
            data.speaker_notes
        )
