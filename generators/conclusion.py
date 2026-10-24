
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import (
    MSO_ANCHOR,
    MSO_AUTO_SIZE,
    PP_ALIGN,
)
from pptx.util import Inches, Pt

from models.schemas import ConclusionSlide


def generate_conclusion_slide(
    prs: Presentation,
    data: ConclusionSlide,
):
    # 1. Tworzenie slajdu
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = data.title

    # 2. Pobieranie obszaru zawartości z szablonu
    placeholder = slide.placeholders[1]

    x = placeholder.left
    top = placeholder.top
    width = placeholder.width
    height = placeholder.height

    # Usuwamy placeholder, aby nie wyświetlał ikon
    element = placeholder._element
    element.getparent().remove(element)

    # 3. Obliczanie wymiarów kart
    points = data.key_points
    count = len(points)

    gap = Inches(0.14)
    min_card_height = Inches(0.60)
    preferred_card_height = Inches(1.02)

    available_height = height - gap * (count - 1)

    if available_height < count * min_card_height:
        raise ValueError(
            "Za mało miejsca na karty podsumowania."
        )

    card_height = min(
        preferred_card_height,
        available_height // count,
    )

    text_size = 19 if count <= 3 else 17

    # 4. Generowanie poszczególnych kart
    for index, point in enumerate(points):

        card_top = top + index * (card_height + gap)

        # Tło karty
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            x,
            card_top,
            width,
            card_height,
        )

        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(241, 245, 249)
        card.line.fill.background()

        # Numer wniosku
        badge_size = min(
            Inches(0.54),
            card_height - Inches(0.16),
        )

        badge = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            x + Inches(0.18),
            card_top + (card_height - badge_size) // 2,
            badge_size,
            badge_size,
        )

        badge.fill.solid()
        badge.fill.fore_color.rgb = RGBColor(31, 62, 89)
        badge.line.fill.background()

        badge_tf = badge.text_frame
        badge_tf.clear()
        badge_tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        badge_tf.margin_left = 0
        badge_tf.margin_right = 0
        badge_tf.margin_top = 0
        badge_tf.margin_bottom = 0

        number = badge_tf.paragraphs[0]
        number.text = f"{index + 1:02d}"
        number.alignment = PP_ALIGN.CENTER
        number.font.bold = True
        number.font.size = Pt(16)
        number.font.color.rgb = RGBColor(255, 255, 255)

        # Treść wniosku
        text_box = slide.shapes.add_textbox(
            x + Inches(0.95),
            card_top + Inches(0.08),
            width - Inches(1.10),
            card_height - Inches(0.16),
        )

        tf = text_box.text_frame
        tf.clear()
        tf.word_wrap = True
        tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE

        tf.margin_left = 0
        tf.margin_right = 0
        tf.margin_top = 0
        tf.margin_bottom = 0

        paragraph = tf.paragraphs[0]
        paragraph.text = point
        paragraph.font.size = Pt(text_size)
        paragraph.font.color.rgb = RGBColor(38, 48, 60)

    # 5. Notatki prelegenta
    if data.speaker_notes:
        slide.notes_slide.notes_text_frame.text = (
            data.speaker_notes
        )
