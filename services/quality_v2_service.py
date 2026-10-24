
from dataclasses import dataclass
from enum import Enum
from statistics import mean

from models.schemas import (
    PresentationSchema,
    TitleContentSlide,
    TwoColumnsSlide,
    ComparisonSlide,
    ConclusionSlide,
    SectionDividerSlide,
    ProcessFlowSlide,
    TimelineSlide,
    KeyMetricsSlide,
    CaseStudySlide,
    QuoteHighlightSlide,
    ReferencesSlide,
)


# ==========================================
# QUALITY MODELS
# ==========================================

class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class QualityIssue:
    slide_number: int
    layout: str
    severity: Severity
    code: str
    message: str


@dataclass
class QualityReport:
    score: int
    issues: list[QualityIssue]
    slide_scores: dict[int, int]

    @property
    def warning_count(self) -> int:
        return sum(
            issue.severity == Severity.WARNING
            for issue in self.issues
        )

    @property
    def error_count(self) -> int:
        return sum(
            issue.severity == Severity.ERROR
            for issue in self.issues
        )

    @property
    def info_count(self) -> int:
        return sum(
            issue.severity == Severity.INFO
            for issue in self.issues
        )


# ==========================================
# QUALITY ENGINE V2
# ==========================================

def evaluate_presentation(
    presentation: PresentationSchema,
) -> QualityReport:

    all_issues = []
    slide_scores = {}

    penalties = {
        Severity.INFO: 1,
        Severity.WARNING: 6,
        Severity.ERROR: 15,
    }

    for slide in presentation.slides:
        issues = []

        def flag(code, severity, message):
            issues.append(
                QualityIssue(
                    slide_number=slide.slide_number,
                    layout=slide.layout.value,
                    severity=severity,
                    code=code,
                    message=message,
                )
            )

        def check_length(text, limit, location):
            if len(text.strip()) > limit:
                flag(
                    "TEXT_TOO_LONG",
                    Severity.WARNING,
                    f"{location}: przekroczono "
                    f"limit {limit} znaków "
                    f"({len(text.strip())}).",
                )

        # ==================================
        # UNIVERSAL RULES
        # ==================================

        check_length(
            slide.title,
            75,
            "Tytuł slajdu",
        )

        # ==================================
        # TITLE CONTENT
        # ==================================

        if isinstance(slide, TitleContentSlide):

            if len(slide.bullet_points) > 6:
                flag(
                    "TOO_MANY_BULLETS",
                    Severity.WARNING,
                    "Zbyt wiele punktów na slajdzie.",
                )

            for bullet in slide.bullet_points:
                check_length(
                    bullet, 110, "Punkt listy"
                )

            total = sum(
                len(b) for b in slide.bullet_points
            )

            if total > 430:
                flag(
                    "SLIDE_DENSITY",
                    Severity.WARNING,
                    "Zbyt duża objętość tekstu "
                    "dla układu Title Content.",
                )

        # ==================================
        # TWO COLUMNS
        # ==================================

        elif isinstance(slide, TwoColumnsSlide):

            for index, column in enumerate(
                slide.columns, start=1
            ):
                total = sum(
                    len(b) for b in column.bullet_points
                )

                if total > 280:
                    flag(
                        "COLUMN_DENSITY",
                        Severity.WARNING,
                        f"Kolumna {index}: zbyt dużo tekstu.",
                    )

                for bullet in column.bullet_points:
                    check_length(
                        bullet,
                        110,
                        f"Kolumna {index}",
                    )

        # ==================================
        # COMPARISON
        # ==================================

        elif isinstance(slide, ComparisonSlide):

            for index, item in enumerate(
                slide.items, start=1
            ):
                total = sum(
                    len(b) for b in item.bullet_points
                )

                if total > 270:
                    flag(
                        "COMPARISON_DENSITY",
                        Severity.WARNING,
                        f"Strona porównania {index} "
                        "zawiera zbyt dużo tekstu.",
                    )

                for bullet in item.bullet_points:
                    check_length(
                        bullet,
                        100,
                        f"Porównanie {index}",
                    )

        # ==================================
        # CONCLUSION
        # ==================================

        elif isinstance(slide, ConclusionSlide):

            for point in slide.key_points:
                check_length(
                    point,
                    120,
                    "Wniosek",
                )

        # ==================================
        # SECTION DIVIDER
        # ==================================

        elif isinstance(slide, SectionDividerSlide):

            check_length(
                slide.subtitle,
                110,
                "Podtytuł sekcji",
            )

        # ==================================
        # PROCESS FLOW
        # ==================================

        elif isinstance(slide, ProcessFlowSlide):

            for index, step in enumerate(
                slide.steps, start=1
            ):
                check_length(
                    step.heading,
                    32,
                    f"Etap {index} — nagłówek",
                )

                check_length(
                    step.description,
                    95,
                    f"Etap {index} — opis",
                )

        # ==================================
        # TIMELINE
        # ==================================

        elif isinstance(slide, TimelineSlide):

            for index, event in enumerate(
                slide.events, start=1
            ):
                check_length(
                    event.heading,
                    32,
                    f"Wydarzenie {index} — nagłówek",
                )

                check_length(
                    event.description,
                    85,
                    f"Wydarzenie {index} — opis",
                )

        # ==================================
        # KEY METRICS
        # ==================================

        elif isinstance(slide, KeyMetricsSlide):

            for index, metric in enumerate(
                slide.metrics, start=1
            ):

                check_length(
                    metric.description,
                    85,
                    f"KPI {index} — opis",
                )

                if len(metric.value) > 15:
                    flag(
                        "METRIC_VALUE_LONG",
                        Severity.WARNING,
                        f"KPI {index}: zbyt długa wartość.",
                    )

                if not metric.source:
                    flag(
                        "METRIC_SOURCE_MISSING",
                        Severity.INFO,
                        f"KPI {index}: warto wskazać "
                        "źródło lub oznaczyć dane "
                        "jako syntetyczne.",
                    )

        # ==================================
        # CASE STUDY
        # ==================================

        elif isinstance(slide, CaseStudySlide):

            sections = {
                "Problem": slide.problem,
                "Analiza": slide.analysis,
                "Rozwiązanie": slide.solution,
                "Rezultat": slide.outcome,
            }

            for name, content in sections.items():
                check_length(
                    content,
                    145,
                    name,
                )

        # ==================================
        # QUOTE HIGHLIGHT
        # ==================================

        elif isinstance(slide, QuoteHighlightSlide):

            check_length(
                slide.statement,
                200,
                "Wyróżniona teza lub cytat",
            )

        # ==================================
        # REFERENCES
        # ==================================

        elif isinstance(slide, ReferencesSlide):

            for index, reference in enumerate(
                slide.references, start=1
            ):
                check_length(
                    reference.citation,
                    135,
                    f"Źródło {index}",
                )

        # ==================================
        # SLIDE SCORE
        # ==================================

        total_penalty = sum(
            penalties[issue.severity]
            for issue in issues
        )

        slide_scores[slide.slide_number] = max(
            0, 100 - total_penalty
        )

        all_issues.extend(issues)

    # Średnia ze slajdów:
    # dłuższe prezentacje nie są karane
    # samą liczbą slajdów.
    overall_score = (
        round(mean(slide_scores.values()))
        if slide_scores
        else 100
    )

    return QualityReport(
        score=overall_score,
        issues=all_issues,
        slide_scores=slide_scores,
    )
