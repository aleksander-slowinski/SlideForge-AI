
from models.schemas import PresentationSchema
from services.ppt_service import create_presentation


def build_demo_presentation(output_path: str) -> PresentationSchema:

    demo_data = {
        "title": "SlideForge AI — Demonstracja",
        "topic": "Automatyzacja tworzenia prezentacji",
        "language": "pl",
        "slides_count": 4,
        "slides": [
            {
                "slide_number": 1,
                "title": "Czym jest SlideForge?",
                "layout": "title_content",
                "bullet_points": [
                    "Automatyczne tworzenie prezentacji PowerPoint",
                    "Integracja modeli językowych z Pythonem",
                    "Walidacja danych przy użyciu Pydantic",
                    "Modułowa architektura aplikacji"
                ],
                "speaker_notes": "Przedstaw główne założenia projektu."
            },
            {
                "slide_number": 2,
                "title": "Architektura systemu",
                "layout": "two_columns",
                "columns": [
                    {
                        "title": "Warstwa AI",
                        "bullet_points": [
                            "Generowanie treści",
                            "Ustrukturyzowany JSON",
                            "Integracja przez API"
                        ]
                    },
                    {
                        "title": "Warstwa Python",
                        "bullet_points": [
                            "Walidacja Pydantic",
                            "Generowanie PPTX",
                            "Kontrola jakości"
                        ]
                    }
                ],
                "speaker_notes": "Wyjaśnij podział odpowiedzialności."
            },
            {
                "slide_number": 3,
                "title": "Porównanie trybów",
                "layout": "comparison",
                "items": [
                    {
                        "title": "Gemini API",
                        "bullet_points": [
                            "Dynamiczna treść",
                            "Wymaga internetu",
                            "Zależność od API"
                        ]
                    },
                    {
                        "title": "Demo Mode",
                        "bullet_points": [
                            "Gotowe dane testowe",
                            "Działa bez internetu",
                            "Brak kosztów API"
                        ]
                    }
                ],
                "speaker_notes": "Porównaj oba tryby działania."
            },
            {
                "slide_number": 4,
                "title": "Najważniejsze wnioski",
                "layout": "conclusion",
                "key_points": [
                    "Silnik działa niezależnie od modelu AI",
                    "Pydantic zapewnia kontrolę struktury danych",
                    "Modułowość ułatwia rozwój aplikacji"
                ],
                "speaker_notes": "Podsumuj możliwości SlideForge."
            }
        ]
    }

    presentation = PresentationSchema.model_validate(demo_data)

    create_presentation(
        data=presentation,
        filename=output_path
    )

    return presentation
