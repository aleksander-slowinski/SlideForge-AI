
from pathlib import Path

from models.schemas import PresentationSchema
from services.ppt_service import create_presentation


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(exist_ok=True)

output_file = OUTPUT_DIR / "advanced_layouts_test.pptx"


data = PresentationSchema.model_validate({
    "title": "SlideForge AI — Advanced Layouts",
    "topic": "Zarządzanie zgodnością w przedsiębiorstwie",
    "language": "pl",
    "slides_count": 3,
    "slides": [
        {
            "slide_number": 1,
            "layout": "section_divider",
            "title": "Zarządzanie ryzykiem i zgodnością",
            "subtitle": (
                "Rozdział II — Identyfikacja, "
                "ocena i monitorowanie ryzyk"
            ),
            "speaker_notes": "Wprowadzenie do drugiej części."
        },
        {
            "slide_number": 2,
            "layout": "process_flow",
            "title": "Proces zarządzania ryzykiem compliance",
            "steps": [
                {
                    "heading": "Identyfikacja",
                    "description": (
                        "Rozpoznanie zagrożeń prawnych "
                        "i regulacyjnych."
                    )
                },
                {
                    "heading": "Ocena",
                    "description": (
                        "Analiza prawdopodobieństwa "
                        "oraz potencjalnych skutków."
                    )
                },
                {
                    "heading": "Planowanie",
                    "description": (
                        "Dobór mechanizmów kontrolnych "
                        "i działań ograniczających ryzyko."
                    )
                },
                {
                    "heading": "Monitoring",
                    "description": (
                        "Bieżąca kontrola wskaźników "
                        "i identyfikacja odchyleń."
                    )
                },
                {
                    "heading": "Raportowanie",
                    "description": (
                        "Przedstawianie wyników "
                        "i rekomendacji zarządowi."
                    )
                }
            ],
            "speaker_notes": "Omów pięć etapów procesu."
        },
        {
            "slide_number": 3,
            "layout": "timeline",
            "title": "Harmonogram wdrożenia systemu compliance BI",
            "events": [
                {
                    "period": "M1",
                    "heading": "Analiza potrzeb",
                    "description": "Określenie wymagań organizacji."
                },
                {
                    "period": "M2",
                    "heading": "Projektowanie",
                    "description": "Model danych i architektura."
                },
                {
                    "period": "M3",
                    "heading": "Integracja",
                    "description": "Połączenie systemów źródłowych."
                },
                {
                    "period": "M4",
                    "heading": "Testowanie",
                    "description": "Walidacja jakości danych i KPI."
                },
                {
                    "period": "M5",
                    "heading": "Uruchomienie",
                    "description": "Wdrożenie raportów i monitoring."
                }
            ],
            "speaker_notes": "Przykładowy harmonogram projektu."
        }
    ]
})


create_presentation(
    data=data,
    filename=str(output_file)
)

print(f"Utworzono prezentację: {output_file}")
