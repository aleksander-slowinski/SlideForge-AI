from pathlib import Path

from pptx import Presentation

from models.schemas import (
    PresentationSchema,
    TitleContentSlide,
    TwoColumnsSlide,
    ComparisonSlide,
    ConclusionSlide,
)

from generators.title_content import generate_title_content_slide
from generators.two_columns import generate_two_columns_slide
from generators.comparison import generate_comparison_slide
from generators.conclusion import generate_conclusion_slide
from generators.advanced_layouts import (
    add_section_divider,
    add_process_flow,
    add_timeline,
)

from models.schemas import (
    SectionDividerSlide,
    ProcessFlowSlide,
    TimelineSlide,
)

from generators.academic_layouts import (
    add_key_metrics,
    add_case_study,
    add_quote_highlight,
    add_references,
)

from models.schemas import (
    KeyMetricsSlide,
    CaseStudySlide,
    QuoteHighlightSlide,
    ReferencesSlide,
)

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = BASE_DIR / "templates" / "template.pptx"


def create_presentation(
    data: PresentationSchema,
    filename: str = "gotowa_prezentacja.pptx",
):
    """
    Tworzy prezentację PowerPoint na podstawie
    zwalidowanego PresentationSchema.
    """

    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Nie znaleziono szablonu: {TEMPLATE_PATH}"
        )

    prs = Presentation(TEMPLATE_PATH)

    # -------------------------------------------------
    # SLAJD TYTUŁOWY
    # -------------------------------------------------

    title_slide = prs.slides.add_slide(prs.slide_layouts[0])

    title_slide.shapes.title.text = data.title
    title_slide.placeholders[1].text = data.topic

    # -------------------------------------------------
    # SLAJDY MERYTORYCZNE
    # -------------------------------------------------

    for slide_data in data.slides:

        if isinstance(slide_data, TitleContentSlide):
            generate_title_content_slide(
                prs,
                slide_data,
            )

        elif isinstance(slide_data, TwoColumnsSlide):
            generate_two_columns_slide(
                prs,
                slide_data,
            )

        elif isinstance(slide_data, ComparisonSlide):
            generate_comparison_slide(
                prs,
                slide_data,
            )

        elif isinstance(slide_data, SectionDividerSlide):
            add_section_divider(prs, slide_data)

        elif isinstance(slide_data, ProcessFlowSlide):
            add_process_flow(prs, slide_data)

        elif isinstance(slide_data, TimelineSlide):
            add_timeline(prs, slide_data)


        elif isinstance(slide_data, ConclusionSlide):
            generate_conclusion_slide(
                prs,
                slide_data,
            )

        elif isinstance(slide_data, KeyMetricsSlide):
            add_key_metrics(prs, slide_data)

        elif isinstance(slide_data, CaseStudySlide):
            add_case_study(prs, slide_data)

        elif isinstance(slide_data, QuoteHighlightSlide):
            add_quote_highlight(prs, slide_data)

        elif isinstance(slide_data, ReferencesSlide):
            add_references(prs, slide_data)

    # -------------------------------------------------
    # ZAPIS
    # -------------------------------------------------

    output_path = Path(filename)

    if not output_path.is_absolute():
        output_path = BASE_DIR / output_path

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    prs.save(output_path)

    print(
        f"[SUKCES] Prezentacja została wygenerowana: "
        f"{output_path}"
    )