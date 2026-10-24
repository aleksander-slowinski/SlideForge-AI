
from urllib.parse import urlparse

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

from services.db_service import get_connection

from services.generation_metrics import GenerationMetrics
from services.quality_v2_service import QualityReport

# ==========================================
# WORD COUNT
# ==========================================

def count_slide_words(slide) -> int:
    """Zlicza słowa widoczne na slajdzie."""

    parts = [slide.title]

    if isinstance(slide, TitleContentSlide):
        parts.extend(slide.bullet_points)

    elif isinstance(slide, TwoColumnsSlide):
        for column in slide.columns:
            parts.append(column.title)
            parts.extend(column.bullet_points)

    elif isinstance(slide, ComparisonSlide):
        for item in slide.items:
            parts.append(item.title)
            parts.extend(item.bullet_points)

    elif isinstance(slide, ConclusionSlide):
        parts.extend(slide.key_points)

    elif isinstance(slide, SectionDividerSlide):
        parts.append(slide.subtitle)

    elif isinstance(slide, ProcessFlowSlide):
        for step in slide.steps:
            parts.append(step.heading)
            parts.append(step.description)

    elif isinstance(slide, TimelineSlide):
        for event in slide.events:
            parts.append(event.period)
            parts.append(event.heading)
            parts.append(event.description)

    elif isinstance(slide, KeyMetricsSlide):
        for metric in slide.metrics:
            parts.append(metric.label)
            parts.append(metric.value)
            parts.append(metric.description)

            if metric.source:
                parts.append(f"Źródło: {metric.source}")

    elif isinstance(slide, CaseStudySlide):
        parts.extend([
            "Problem",
            slide.problem,
            "Analiza",
            slide.analysis,
            "Rozwiązanie",
            slide.solution,
            "Rezultat",
            slide.outcome,
        ])

    elif isinstance(slide, QuoteHighlightSlide):
        parts.append(slide.statement)

        if slide.attribution:
            parts.append(slide.attribution)

    elif isinstance(slide, ReferencesSlide):
        for reference in slide.references:
            parts.append(reference.citation)

            if reference.url:
                domain = urlparse(
                    str(reference.url)
                ).netloc

                parts.append(domain)

    return len(" ".join(parts).split())


# ==========================================
# START GENERATION
# ==========================================

def start_generation(
    mode: str,
    topic: str,
    requested_slides: int,
) -> int:
    """Rejestruje rozpoczęcie generowania."""

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.GenerationRun
                (
                    GenerationMode,
                    Topic,
                    RequestedSlides,
                    Status
                )
            OUTPUT INSERTED.RunID
            VALUES (?, ?, ?, 'STARTED')
            """,
            mode,
            topic,
            requested_slides,
        )

        run_id = int(cursor.fetchone()[0])

        connection.commit()

        return run_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ==========================================
# FINISH GENERATION
# ==========================================

def finish_generation(
    run_id: int,
    presentation: PresentationSchema,
    duration_ms: int,
) -> None:
    """Zapisuje sukces i metryki slajdów."""

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE dbo.GenerationRun
            SET
                Status = 'SUCCESS',
                FinishedAtUtc = SYSUTCDATETIME(),
                GeneratedSlides = ?,
                DurationMs = ?
            WHERE RunID = ?
              AND Status = 'STARTED'
            """,
            len(presentation.slides),
            duration_ms,
            run_id,
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "Nie znaleziono aktywnego generowania."
            )

        for slide in presentation.slides:
            cursor.execute(
                """
                INSERT INTO dbo.GeneratedSlide
                    (
                        RunID,
                        SlideNumber,
                        LayoutType,
                        WordCount
                    )
                VALUES (?, ?, ?, ?)
                """,
                run_id,
                slide.slide_number,
                slide.layout.value,
                count_slide_words(slide),
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ==========================================
# FAIL GENERATION
# ==========================================

def fail_generation(
    run_id: int,
    duration_ms: int,
    error_code: str,
) -> None:
    """Rejestruje nieudaną próbę generowania."""

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE dbo.GenerationRun
            SET
                Status = 'FAILED',
                FinishedAtUtc = SYSUTCDATETIME(),
                DurationMs = ?,
                ErrorCode = ?
            WHERE RunID = ?
              AND Status = 'STARTED'
            """,
            duration_ms,
            error_code[:30],
            run_id,
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "Nie znaleziono aktywnego generowania."
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ==========================================
# SAVE QUALITY REPORT
# ==========================================

def save_quality_report(
    run_id: int,
    report: QualityReport,
) -> None:
    """
    Zapisuje wynik jakości oraz szczegółowe problemy.

    Operacja jest transakcyjna.
    Ponowny zapis dla RunID zastępuje poprzedni raport.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Usunięcie wcześniejszej oceny tego RunID,
        # jeśli raport był już zapisywany.
        cursor.execute(
            """
            DELETE FROM dbo.QualityIssue
            WHERE RunID = ?
            """,
            run_id,
        )

        cursor.execute(
            """
            DELETE FROM dbo.GenerationQuality
            WHERE RunID = ?
            """,
            run_id,
        )

        # Raport może dotyczyć wyłącznie
        # zakończonej sukcesem generacji.
        cursor.execute(
            """
            INSERT INTO dbo.GenerationQuality
            (
                RunID,
                QualityScore,
                WarningCount,
                ErrorCount,
                InfoCount,
                QualityEngineVersion
            )
            SELECT
                g.RunID,
                ?, ?, ?, ?, ?
            FROM dbo.GenerationRun AS g
            WHERE g.RunID = ?
              AND g.Status = 'SUCCESS'
            """,
            report.score,
            report.warning_count,
            report.error_count,
            report.info_count,
            "2.0",
            run_id,
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "Nie znaleziono udanej generacji "
                f"o RunID={run_id}."
            )

        # Zapisywanie szczegółowych problemów.
        for issue in report.issues:
            cursor.execute(
                """
                INSERT INTO dbo.QualityIssue
                (
                    RunID,
                    SlideNumber,
                    LayoutType,
                    Severity,
                    IssueCode,
                    Message
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                run_id,
                issue.slide_number,
                issue.layout,
                issue.severity.value,
                issue.code,
                issue.message,
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def save_run_metrics(
    run_id: int,
    metrics: GenerationMetrics,
) -> None:
    """Zapisuje metryki wykonania do GenerationRun."""

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE dbo.GenerationRun
            SET
                ModelName = ?,
                ThinkingLevel = ?,
                LLMDurationMs = ?,
                ValidationDurationMs = ?,
                PptxDurationMs = ?,
                PromptTokens = ?,
                OutputTokens = ?,
                ThinkingTokens = ?,
                TotalTokens = ?
            WHERE RunID = ?
            """,
            metrics.model_name,
            metrics.thinking_level,
            metrics.llm_duration_ms,
            metrics.validation_duration_ms,
            metrics.pptx_duration_ms,
            metrics.prompt_tokens,
            metrics.output_tokens,
            metrics.thinking_tokens,
            metrics.total_tokens,
            run_id,
        )

        if cursor.rowcount != 1:
            raise ValueError(
                f"Nie znaleziono RunID={run_id}."
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
