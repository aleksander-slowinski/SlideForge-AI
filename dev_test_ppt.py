from models.schemas import PresentationSchema
from services.ppt_service import create_presentation


test_presentation = {
    "title": "Test SlideForge",
    "topic": "Test wszystkich layoutów",
    "language": "pl",
    "slides_count": 4,
    "slides": [
        {
            "slide_number": 1,
            "title": "Slajd tekstowy",
            "layout": "title_content",
            "bullet_points": [
                "Pierwszy punkt",
                "Drugi punkt",
                "Trzeci punkt",
            ],
            "speaker_notes": "Notatki do slajdu tekstowego.",
        },
        {
            "slide_number": 2,
            "title": "Dwie kolumny",
            "layout": "two_columns",
            "columns": [
                {
                    "title": "Lewa strona",
                    "bullet_points": [
                        "Punkt A",
                        "Punkt B",
                    ],
                },
                {
                    "title": "Prawa strona",
                    "bullet_points": [
                        "Punkt C",
                        "Punkt D",
                    ],
                },
            ],
            "speaker_notes": "Notatki do slajdu dwukolumnowego.",
        },
        {
            "slide_number": 3,
            "title": "Porównanie",
            "layout": "comparison",
            "items": [
                {
                    "title": "Opcja A",
                    "bullet_points": [
                        "Cecha A1",
                        "Cecha A2",
                    ],
                },
                {
                    "title": "Opcja B",
                    "bullet_points": [
                        "Cecha B1",
                        "Cecha B2",
                    ],
                },
            ],
            "speaker_notes": "Notatki do porównania.",
        },
        {
            "slide_number": 4,
            "title": "Podsumowanie",
            "layout": "conclusion",
            "key_points": [
                "Najważniejszy wniosek",
                "Drugi wniosek",
                "Trzeci wniosek",
            ],
            "speaker_notes": "Notatki końcowe.",
        },
    ],
}


presentation = PresentationSchema.model_validate(test_presentation)

create_presentation(
    presentation,
    "output/test_all_layouts.pptx",
)

print("TEST ZAKOŃCZONY SUKCESEM")