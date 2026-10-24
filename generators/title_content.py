from pptx import Presentation

from models.schemas import TitleContentSlide


def generate_title_content_slide(
    prs: Presentation,
    data: TitleContentSlide,
):
    slide = prs.slides.add_slide(prs.slide_layouts[1])

    slide.shapes.title.text = data.title

    text_frame = slide.placeholders[1].text_frame
    text_frame.clear()

    for index, point in enumerate(data.bullet_points):
        paragraph = (
            text_frame.paragraphs[0]
            if index == 0
            else text_frame.add_paragraph()
        )

        paragraph.text = point
        paragraph.level = 0

    if data.speaker_notes:
        slide.notes_slide.notes_text_frame.text = data.speaker_notes