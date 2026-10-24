
from urllib.parse import urlparse

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import (
    MSO_AUTO_SIZE,
    MSO_ANCHOR,
    PP_ALIGN,
)
from pptx.util import Pt

from generators.advanced_layouts import (
    NAVY,
    BLUE,
    LIGHT,
    WHITE,
    GRAY,
    prepare_content_slide,
    add_notes,
)


ACCENT = RGBColor(57, 153, 169)


def _rectangle(
    slide, x, y, width, height,
    fill, rounded=True
):
    shape_type = (
        MSO_SHAPE.ROUNDED_RECTANGLE
        if rounded else MSO_SHAPE.RECTANGLE
    )

    shape = slide.shapes.add_shape(
        shape_type,
        int(x), int(y),
        int(width), int(height),
    )

    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.fill.background()

    return shape


def _text(
    slide, value, x, y, width, height,
    size=18, color=NAVY, bold=False,
    align=PP_ALIGN.LEFT, link=None
):
    shape = slide.shapes.add_textbox(
        int(x), int(y),
        int(width), int(height),
    )

    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE

    frame.margin_left = 0
    frame.margin_right = 0
    frame.margin_top = 0
    frame.margin_bottom = 0

    paragraph = frame.paragraphs[0]
    paragraph.alignment = align

    run = paragraph.add_run()
    run.text = str(value)
    run.font.name = "Aptos"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color

    if link:
        run.hyperlink.address = link

    return shape


# ==========================================
# KEY METRICS
# ==========================================

def add_key_metrics(prs, data):
    slide = prepare_content_slide(prs, data.title)

    width = prs.slide_width
    height = prs.slide_height

    count = len(data.metrics)

    # 4 KPI = siatka 2x2
    # 2 lub 3 KPI = jeden rząd
    columns = 2 if count == 4 else count
    rows = 2 if count == 4 else 1

    left = int(width * 0.07)
    top = int(height * 0.235)

    total_width = int(width * 0.86)
    total_height = int(height * 0.61)

    gap_x = int(width * 0.025)
    gap_y = int(height * 0.035)

    card_width = (
        total_width - gap_x * (columns - 1)
    ) // columns

    card_height = (
        total_height - gap_y * (rows - 1)
    ) // rows

    for i, metric in enumerate(data.metrics):
        col = i % columns
        row = i // columns

        x = left + col * (card_width + gap_x)
        y = top + row * (card_height + gap_y)

        _rectangle(
            slide, x, y,
            card_width, card_height, LIGHT
        )

        # Pasek akcentowy
        _rectangle(
            slide, x, y,
            int(width * 0.006),
            card_height,
            ACCENT,
            rounded=False,
        )

        inner_x = x + int(card_width * 0.075)
        inner_w = int(card_width * 0.84)

        # Nazwa wskaźnika
        _text(
            slide, metric.label,
            inner_x,
            y + int(card_height * 0.13),
            inner_w,
            int(card_height * 0.15),
            size=17,
            bold=True,
            color=GRAY,
        )

        # Duża wartość KPI
        _text(
            slide, metric.value,
            inner_x,
            y + int(card_height * 0.30),
            inner_w,
            int(card_height * 0.32),
            size=42 if rows == 1 else 35,
            bold=True,
        )

        # Krótki komentarz
        _text(
            slide, metric.description,
            inner_x,
            y + int(card_height * 0.65),
            inner_w,
            int(card_height * 0.20),
            size=15,
            color=GRAY,
        )

        # Opcjonalne źródło
        if metric.source:
            _text(
                slide,
                f"Źródło: {metric.source}",
                inner_x,
                y + int(card_height * 0.86),
                inner_w,
                int(card_height * 0.11),
                size=11,
                color=GRAY,
            )

    add_notes(slide, data.speaker_notes)


# ==========================================
# CASE STUDY
# ==========================================

def add_case_study(prs, data):
    slide = prepare_content_slide(prs, data.title)

    width = prs.slide_width
    height = prs.slide_height

    sections = [
        ("PROBLEM", data.problem),
        ("ANALIZA", data.analysis),
        ("ROZWIĄZANIE", data.solution),
        ("REZULTAT", data.outcome),
    ]

    left = int(width * 0.07)
    top = int(height * 0.23)

    gap_x = int(width * 0.03)
    gap_y = int(height * 0.035)

    card_width = (
        int(width * 0.86) - gap_x
    ) // 2

    card_height = (
        int(height * 0.62) - gap_y
    ) // 2

    for i, (heading, description) in enumerate(sections):
        x = left + (i % 2) * (card_width + gap_x)
        y = top + (i // 2) * (card_height + gap_y)

        _rectangle(
            slide, x, y,
            card_width, card_height, LIGHT
        )

        badge_x = x + int(card_width * 0.055)
        badge_y = y + int(card_height * 0.13)
        badge_w = int(card_width * 0.09)
        badge_h = int(card_height * 0.22)

        _rectangle(
            slide,
            badge_x, badge_y,
            badge_w, badge_h,
            BLUE,
        )

        _text(
            slide, f"{i + 1:02d}",
            badge_x, badge_y,
            badge_w, badge_h,
            size=14,
            color=WHITE,
            bold=True,
            align=PP_ALIGN.CENTER,
        )

        _text(
            slide, heading,
            x + int(card_width * 0.18),
            y + int(card_height * 0.13),
            int(card_width * 0.75),
            int(card_height * 0.22),
            size=18,
            bold=True,
        )

        _text(
            slide, description,
            x + int(card_width * 0.055),
            y + int(card_height * 0.40),
            int(card_width * 0.88),
            int(card_height * 0.47),
            size=17,
            color=GRAY,
        )

    add_notes(slide, data.speaker_notes)


# ==========================================
# QUOTE HIGHLIGHT
# ==========================================

def add_quote_highlight(prs, data):
    slide = prepare_content_slide(prs, data.title)

    width = prs.slide_width
    height = prs.slide_height

    x = int(width * 0.08)
    y = int(height * 0.26)
    w = int(width * 0.84)
    h = int(height * 0.55)

    _rectangle(slide, x, y, w, h, LIGHT)

    _rectangle(
        slide, x, y,
        int(width * 0.008),
        h,
        ACCENT,
        rounded=False,
    )

    label = (
        "CYTAT"
        if data.kind == "quotation"
        else "KLUCZOWA TEZA"
    )

    _text(
        slide, label,
        x + int(w * 0.075),
        y + int(h * 0.10),
        int(w * 0.80),
        int(h * 0.12),
        size=13,
        color=BLUE,
        bold=True,
    )

    is_long_statement = len(data.statement) > 180

    _text(
        slide,
        data.statement,
        x + int(w * 0.075),
        y + int(h * 0.24),
        int(w * 0.83),
        int(h * 0.47),
        size=23 if is_long_statement else 26,
        bold=not is_long_statement,
    )

    if data.attribution:
        _text(
            slide, data.attribution,
            x + int(w * 0.075),
            y + int(h * 0.77),
            int(w * 0.80),
            int(h * 0.13),
            size=15,
            color=GRAY,
        )

    add_notes(slide, data.speaker_notes)


# ==========================================
# REFERENCES
# ==========================================

def add_references(prs, data):
    slide = prepare_content_slide(prs, data.title)

    width = prs.slide_width
    height = prs.slide_height

    left = int(width * 0.075)
    top = int(height * 0.215)

    total_width = int(width * 0.85)
    total_height = int(height * 0.66)

    gap = int(height * 0.015)
    count = len(data.references)

    card_height = (
        total_height - gap * (count - 1)
    ) // count

    for i, reference in enumerate(data.references):
        y = top + i * (card_height + gap)

        _rectangle(
            slide, left, y,
            total_width, card_height, LIGHT
        )

        number_width = int(total_width * 0.075)

        _text(
            slide, f"{i + 1:02d}",
            left + int(total_width * 0.02),
            y + int(card_height * 0.19),
            number_width,
            int(card_height * 0.55),
            size=17,
            bold=True,
            color=BLUE,
        )

        text_x = left + int(total_width * 0.12)
        text_w = int(total_width * 0.84)

        if reference.url:
            _text(
                slide, reference.citation,
                text_x,
                y + int(card_height * 0.10),
                text_w,
                int(card_height * 0.48),
                size=16,
            )

            url = str(reference.url)
            domain = urlparse(url).netloc

            _text(
                slide, domain,
                text_x,
                y + int(card_height * 0.60),
                text_w,
                int(card_height * 0.22),
                size=11,
                color=BLUE,
                link=url,
            )

        else:
            _text(
                slide, reference.citation,
                text_x,
                y + int(card_height * 0.18),
                text_w,
                int(card_height * 0.64),
                size=17,
            )

    add_notes(slide, data.speaker_notes)
