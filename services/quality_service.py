
from models.schemas import (
    PresentationSchema,
    TitleContentSlide,
    TwoColumnsSlide,
    ComparisonSlide,
    ConclusionSlide,
)


def analyze_presentation(data: PresentationSchema) -> list[str]:
    warnings = []

    for slide in data.slides:
        number = slide.slide_number

        # Kontrola długości tytułu
        if len(slide.title) > 75:
            warnings.append(
                f"Slajd {number}: zbyt długi tytuł "
                f"({len(slide.title)} znaków)."
            )

        # Pobieranie tekstu zależnie od layoutu
        if isinstance(slide, TitleContentSlide):
            points = slide.bullet_points

        elif isinstance(slide, TwoColumnsSlide):
            points = [
                point
                for column in slide.columns
                for point in column.bullet_points
            ]

        elif isinstance(slide, ComparisonSlide):
            points = [
                point
                for item in slide.items
                for point in item.bullet_points
            ]

        elif isinstance(slide, ConclusionSlide):
            points = slide.key_points

        else:
            continue

        # Kontrola pojedynczych punktów
        for point in points:
            if len(point) > 110:
                warnings.append(
                    f"Slajd {number}: punkt tekstowy "
                    f"przekracza 110 znaków."
                )

        # Kontrola całkowitej ilości tekstu
        total_characters = sum(len(point) for point in points)

        if total_characters > 430:
            warnings.append(
                f"Slajd {number}: zbyt dużo tekstu "
                f"({total_characters} znaków)."
            )

    return warnings
