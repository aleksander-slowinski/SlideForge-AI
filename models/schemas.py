from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator
from pydantic import HttpUrl

class LayoutType(str, Enum):
    TITLE_CONTENT = "title_content"
    TWO_COLUMNS = "two_columns"
    COMPARISON = "comparison"
    CONCLUSION = "conclusion"
    SECTION_DIVIDER = "section_divider"
    PROCESS_FLOW = "process_flow"
    TIMELINE = "timeline"
    KEY_METRICS = "key_metrics"
    CASE_STUDY = "case_study"
    QUOTE_HIGHLIGHT = "quote_highlight"
    REFERENCES = "references"


class BaseSlideSchema(BaseModel):
    slide_number: int = Field(ge=1)
    title: str = Field(
        min_length=3,
        max_length=150,
    )
    speaker_notes: str | None = None


class TitleContentSlide(BaseSlideSchema):
    layout: Literal[LayoutType.TITLE_CONTENT]
    bullet_points: list[str] = Field(
        min_length=1,
        max_length=6,
    )


class ColumnSchema(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=60,
    )
    bullet_points: list[str] = Field(
        min_length=1,
        max_length=5,
    )


class TwoColumnsSlide(BaseSlideSchema):
    layout: Literal[LayoutType.TWO_COLUMNS]
    columns: list[ColumnSchema] = Field(
        min_length=2,
        max_length=2,
    )


class ComparisonItemSchema(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=60,
    )
    bullet_points: list[str] = Field(
        min_length=1,
        max_length=5,
    )


class ComparisonSlide(BaseSlideSchema):
    layout: Literal[LayoutType.COMPARISON]
    items: list[ComparisonItemSchema] = Field(
        min_length=2,
        max_length=2,
    )


class ConclusionSlide(BaseSlideSchema):
    layout: Literal[LayoutType.CONCLUSION]
    key_points: list[str] = Field(
        min_length=1,
        max_length=5,
    )


class SectionDividerSlide(BaseModel):
    slide_number: int = Field(ge=1)
    layout: Literal[LayoutType.SECTION_DIVIDER]
    title: str = Field(min_length=1, max_length=100)
    subtitle: str = Field(default="", max_length=160)
    speaker_notes: str = ""


class ProcessStep(BaseModel):
    heading: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=110)


class ProcessFlowSlide(BaseModel):
    slide_number: int = Field(ge=1)
    layout: Literal[LayoutType.PROCESS_FLOW]
    title: str = Field(min_length=1, max_length=100)
    steps: list[ProcessStep] = Field(
        min_length=3,
        max_length=5
    )
    speaker_notes: str = ""


class TimelineEvent(BaseModel):
    period: str = Field(min_length=1, max_length=25)
    heading: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=100)


class TimelineSlide(BaseModel):
    slide_number: int = Field(ge=1)
    layout: Literal[LayoutType.TIMELINE]
    title: str = Field(min_length=1, max_length=100)
    events: list[TimelineEvent] = Field(
        min_length=3,
        max_length=5
    )
    speaker_notes: str = ""


class KeyMetric(BaseModel):
    label: str = Field(min_length=1, max_length=45)
    value: str = Field(min_length=1, max_length=25)
    description: str = Field(default="", max_length=100)
    source: str | None = Field(default=None, max_length=100)


class KeyMetricsSlide(BaseModel):
    slide_number: int = Field(ge=1)
    layout: Literal[LayoutType.KEY_METRICS]
    title: str = Field(min_length=1, max_length=100)
    metrics: list[KeyMetric] = Field(
        min_length=2,
        max_length=4,
    )
    speaker_notes: str = ""


class CaseStudySlide(BaseModel):
    slide_number: int = Field(ge=1)
    layout: Literal[LayoutType.CASE_STUDY]
    title: str = Field(min_length=1, max_length=100)

    problem: str = Field(min_length=1, max_length=170)
    analysis: str = Field(min_length=1, max_length=170)
    solution: str = Field(min_length=1, max_length=170)
    outcome: str = Field(min_length=1, max_length=170)

    speaker_notes: str = ""


class QuoteHighlightSlide(BaseModel):
    slide_number: int = Field(ge=1)
    layout: Literal[LayoutType.QUOTE_HIGHLIGHT]
    title: str = Field(min_length=1, max_length=100)

    kind: Literal["thesis", "quotation"] = "thesis"
    statement: str = Field(min_length=1, max_length=260)
    attribution: str | None = Field(
        default=None,
        max_length=120,
    )

    speaker_notes: str = ""

    @model_validator(mode="after")
    def validate_quotation(self):
        if self.kind == "quotation" and not self.attribution:
            raise ValueError(
                "Cytat wymaga wskazania autora lub źródła."
            )
        return self


class ReferenceEntry(BaseModel):
    citation: str = Field(min_length=1, max_length=180)
    url: HttpUrl | None = None


class ReferencesSlide(BaseModel):
    slide_number: int = Field(ge=1)
    layout: Literal[LayoutType.REFERENCES]
    title: str = Field(min_length=1, max_length=100)

    references: list[ReferenceEntry] = Field(
        min_length=1,
        max_length=5,
    )

    speaker_notes: str = ""


SlideSchema = Annotated[
    TitleContentSlide
    | TwoColumnsSlide
    | ComparisonSlide
    | ConclusionSlide
    | SectionDividerSlide
    | ProcessFlowSlide
    | TimelineSlide
    | KeyMetricsSlide
    | CaseStudySlide
    | QuoteHighlightSlide
    | ReferencesSlide,
    Field(discriminator="layout"),
]


class PresentationSchema(BaseModel):
    title: str = Field(
        min_length=3,
        max_length=150,
    )

    topic: str = Field(
        min_length=3,
        max_length=200,
    )

    language: Literal["pl"] = "pl"

    slides_count: int = Field(
        ge=1,
        le=25,
    )

    slides: list[SlideSchema] = Field(
        min_length=1,
        max_length=30,
    )

    @model_validator(mode="after")
    def validate_presentation(self):

        if self.slides_count != len(self.slides):
            raise ValueError(
                f"slides_count ({self.slides_count}) "
                f"nie odpowiada liczbie slajdów "
                f"({len(self.slides)})"
            )

        slide_numbers = [
            slide.slide_number
            for slide in self.slides
        ]

        expected_numbers = list(
            range(1, self.slides_count + 1)
        )

        if slide_numbers != expected_numbers:
            raise ValueError(
                f"Nieprawidłowa numeracja slajdów. "
                f"Oczekiwano {expected_numbers}, "
                f"otrzymano {slide_numbers}"
            )

        return self
    
