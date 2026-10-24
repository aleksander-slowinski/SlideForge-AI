
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt
from pptx.enum.text import MSO_AUTO_SIZE


NAVY = RGBColor(31, 63, 91)
BLUE = RGBColor(54, 105, 143)
LIGHT = RGBColor(238, 243, 248)
WHITE = RGBColor(255, 255, 255)
GRAY = RGBColor(78, 91, 105)


def add_text(
    slide, text, x, y, width, height,
    font_size=18, bold=False,
    color=NAVY, align=PP_ALIGN.LEFT
):
    box = slide.shapes.add_textbox(
        int(x), int(y), int(width), int(height)
    )

    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    frame.margin_left = Inches(0.05)
    frame.margin_right = Inches(0.05)

    paragraph = frame.paragraphs[0]
    paragraph.alignment = align

    run = paragraph.add_run()
    run.text = text
    run.font.name = "Aptos"
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color

    return box


def add_rectangle(
    slide, x, y, width, height,
    color, rounded=False
):
    shape_type = (
        MSO_SHAPE.ROUNDED_RECTANGLE
        if rounded else MSO_SHAPE.RECTANGLE
    )

    shape = slide.shapes.add_shape(
        shape_type,
        int(x), int(y), int(width), int(height)
    )

    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()

    return shape



def prepare_content_slide(prs, title):
    slide = prs.slides.add_slide(prs.slide_layouts[1])

    title_shape = slide.shapes.title
    title_shape.text = title

    text_frame = title_shape.text_frame
    text_frame.word_wrap = True
    text_frame.auto_size = (
        MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    )

    # Adaptacyjne dopasowanie wielkości tytułu
    title_length = len(title.strip())

    if title_length > 65:
        font_size = 26
    elif title_length > 42:
        font_size = 30
    else:
        font_size = 34

    for paragraph in text_frame.paragraphs:
        for run in paragraph.runs:
            run.font.size = Pt(font_size)

    # Usuwamy nieużywane placeholders
    for shape in list(slide.shapes):
        if (
            shape.is_placeholder
            and shape.shape_id != title_shape.shape_id
        ):
            element = shape._element
            element.getparent().remove(element)

    return slide



def add_notes(slide, notes):
    if notes:
        slide.notes_slide.notes_text_frame.text = notes


# ==========================================
# SECTION DIVIDER
# ==========================================

def add_section_divider(prs, data):
    slide = prs.slides.add_slide(prs.slide_layouts[1])

    # Ten layout samodzielnie rysuje tytuł.
    for shape in list(slide.shapes):
        if shape.is_placeholder:
            element = shape._element
            element.getparent().remove(element)

    width = prs.slide_width
    height = prs.slide_height

    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = NAVY

    add_rectangle(
        slide,
        width * 0.10,
        height * 0.31,
        width * 0.008,
        height * 0.35,
        RGBColor(89, 184, 205),
    )

    add_text(
        slide,
        data.title,
        width * 0.14,
        height * 0.31,
        width * 0.75,
        height * 0.22,
        font_size=38,
        bold=True,
        color=WHITE,
    )

    if data.subtitle:
        add_text(
            slide,
            data.subtitle,
            width * 0.14,
            height * 0.55,
            width * 0.72,
            height * 0.12,
            font_size=19,
            color=WHITE,
        )

    add_notes(slide, data.speaker_notes)


# ==========================================
# PROCESS FLOW
# ==========================================

def add_process_flow(prs, data):
    slide = prepare_content_slide(prs, data.title)

    width = prs.slide_width
    height = prs.slide_height

    count = len(data.steps)

    left = int(width * 0.06)
    usable_width = int(width * 0.88)
    gap = int(width * 0.012)

    card_width = (
        usable_width - gap * (count - 1)
    ) // count

    y = int(height * 0.30)
    card_height = int(height * 0.46)

    for index, step in enumerate(data.steps):
        x = left + index * (card_width + gap)

        add_rectangle(
            slide, x, y,
            card_width, card_height,
            LIGHT, rounded=True,
        )

        add_rectangle(
            slide,
            x + int(card_width * 0.08),
            y + int(height * 0.035),
            int(card_width * 0.23),
            int(height * 0.075),
            NAVY,
            rounded=True,
        )

        add_text(
            slide,
            f"{index + 1:02d}",
            x + int(card_width * 0.08),
            y + int(height * 0.035),
            int(card_width * 0.23),
            int(height * 0.075),
            font_size=17,
            bold=True,
            color=WHITE,
            align=PP_ALIGN.CENTER,
        )

        add_text(
            slide,
            step.heading,
            x + int(card_width * 0.07),
            y + int(height * 0.12),
            int(card_width * 0.86),
            int(height * 0.10),
            font_size=17 if count <= 4 else 15,
            bold=True,
        )

        add_text(
            slide,
            step.description,
            x + int(card_width * 0.07),
            y + int(height * 0.20),
            int(card_width * 0.86),
            int(height * 0.17),
            font_size=15 if count <= 4 else 13,
            color=GRAY,
        )

    add_notes(slide, data.speaker_notes)


# ==========================================
# TIMELINE
# ==========================================

def add_timeline(prs, data):
    slide = prepare_content_slide(prs, data.title)

    width = prs.slide_width
    height = prs.slide_height

    left = int(width * 0.07)
    usable_width = int(width * 0.86)
    count = len(data.events)

    item_width = usable_width // count

    line_y = int(height * 0.50)

    add_rectangle(
        slide,
        left,
        line_y,
        usable_width,
        Inches(0.045),
        BLUE,
    )

    for index, event in enumerate(data.events):
        item_x = left + index * item_width
        center_x = item_x + item_width // 2

        dot_size = Inches(0.20)

        dot = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            int(center_x - dot_size / 2),
            int(line_y - dot_size / 2),
            dot_size,
            dot_size,
        )

        dot.fill.solid()
        dot.fill.fore_color.rgb = NAVY
        dot.line.fill.background()

        add_text(
            slide,
            event.period,
            item_x,
            height * 0.34,
            item_width,
            height * 0.09,
            font_size=18,
            bold=True,
            align=PP_ALIGN.CENTER,
        )

        add_text(
            slide,
            event.heading,
            item_x,
            height * 0.57,
            item_width,
            height * 0.09,
            font_size=16,
            bold=True,
            align=PP_ALIGN.CENTER,
        )

        add_text(
            slide,
            event.description,
            item_x,
            height * 0.67,
            item_width,
            height * 0.15,
            font_size=14 if count <= 4 else 12,
            color=GRAY,
            align=PP_ALIGN.CENTER,
        )

    add_notes(slide, data.speaker_notes)
