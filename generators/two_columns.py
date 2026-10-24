
from pptx import Presentation

from models.schemas import TwoColumnsSlide
from generators.text_utils import fill_column


def generate_two_columns_slide(
    prs: Presentation,
    data: TwoColumnsSlide,
):
    slide = prs.slides.add_slide(prs.slide_layouts[3])

    slide.shapes.title.text = data.title

    for placeholder_index, column in zip((1, 2), data.columns):
        text_frame = slide.placeholders[placeholder_index].text_frame

        fill_column(
            text_frame=text_frame,
            heading=column.title,
            bullet_points=column.bullet_points,
        )

    if data.speaker_notes:
        slide.notes_slide.notes_text_frame.text = data.speaker_notes
