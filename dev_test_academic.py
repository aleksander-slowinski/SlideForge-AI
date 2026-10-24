
from pathlib import Path

from models.schemas import PresentationSchema
from services.ppt_service import create_presentation


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

output_file = OUTPUT_DIR / "academic_layouts_test.pptx"


data = PresentationSchema.model_validate({
    "title": "SlideForge AI — Academic Layouts",
    "topic": "Analityka danych i compliance",
    "language": "pl",
    "slides_count": 4,
    "slides": [
        {
            "slide_number": 1,
            "layout": "key_metrics",
            "title": "Kluczowe wskaźniki monitorowania compliance",
            "metrics": [
                {
                    "label": "Zgodność procesów",
                    "value": "94,8%",
                    "description": "Udział procesów spełniających wewnętrzne wymagania kontrolne.",
                    "source": "Dane syntetyczne",
                },
                {
                    "label": "Średni czas reakcji",
                    "value": "12,5 h",
                    "description": "Przeciętny czas od wykrycia incydentu do rozpoczęcia analizy.",
                    "source": "Dane syntetyczne",
                },
                {
                    "label": "Incydenty",
                    "value": "127",
                    "description": "Liczba zgłoszeń zarejestrowanych w analizowanym okresie.",
                    "source": "Dane syntetyczne",
                },
                {
                    "label": "Audytowane procesy",
                    "value": "85%",
                    "description": "Odsetek procesów objętych zaplanowanymi czynnościami audytowymi.",
                    "source": "Dane syntetyczne",
                },
            ],
            "speaker_notes": "Wszystkie dane są syntetyczne i służą wyłącznie testom.",
        },
        {
            "slide_number": 2,
            "layout": "case_study",
            "title": "Studium przypadku — poprawa jakości danych",
            "problem": (
                "Organizacja wykryła rozbieżności pomiędzy danymi "
                "przechowywanymi w systemie CRM a dokumentacją "
                "źródłową wykorzystywaną podczas audytów."
            ),
            "analysis": (
                "Przeprowadzono analizę powtarzających się błędów, "
                "zidentyfikowano niespójne identyfikatory oraz "
                "brak jednolitych zasad aktualizacji danych."
            ),
            "solution": (
                "Wprowadzono automatyczne reguły walidacji, "
                "ujednolicono słowniki referencyjne oraz "
                "zbudowano raport monitorujący jakość danych."
            ),
            "outcome": (
                "Uzyskano większą przejrzystość procesu kontroli "
                "oraz możliwość szybszego identyfikowania rekordów "
                "wymagających ponownej weryfikacji."
            ),
            "speaker_notes": "Hipotetyczny przykład wdrożenia.",
        },
        {
            "slide_number": 3,
            "layout": "quote_highlight",
            "title": "Kluczowa teza dotycząca jakości danych",
            "kind": "thesis",
            "statement": (
                "Automatyzacja raportowania nie zastępuje "
                "odpowiedzialności za jakość informacji. "
                "Skuteczne wykorzystanie Business Intelligence "
                "wymaga spójnych danych, jasnych zasad ich "
                "przetwarzania oraz odpowiednio zaprojektowanych "
                "mechanizmów kontrolnych."
            ),
            "attribution": "Teza analityczna — SlideForge",
            "speaker_notes": "Omów znaczenie jakości danych.",
        },
        {
            "slide_number": 4,
            "layout": "references",
            "title": "Bibliografia i materiały źródłowe",
            "references": [
                {
                    "citation": (
                        "Przykładowy dokument A (2024). "
                        "Wprowadzenie do zarządzania zgodnością "
                        "w przedsiębiorstwie."
                    ),
                    "url": "https://example.com/a",
                },
                {
                    "citation": (
                        "Przykładowy dokument B (2023). "
                        "Metody zapewniania jakości danych "
                        "w procesach analitycznych."
                    ),
                },
                {
                    "citation": (
                        "Przykładowy dokument C (2025). "
                        "Business Intelligence jako narzędzie "
                        "wspierające audyt wewnętrzny."
                    ),
                },
                {
                    "citation": (
                        "Przykładowy dokument D (2024). "
                        "Projektowanie mechanizmów kontrolnych "
                        "w systemach informacyjnych."
                    ),
                },
                {
                    "citation": (
                        "Przykładowy dokument E (2022). "
                        "Monitorowanie ryzyk operacyjnych "
                        "z wykorzystaniem wskaźników KPI."
                    ),
                },
            ],
            "speaker_notes": (
                "Wszystkie pozycje bibliograficzne są fikcyjne "
                "i służą wyłącznie testowi wizualnemu."
            ),
        },
    ],
})


create_presentation(
    data=data,
    filename=str(output_file),
)

print(f"Utworzono: {output_file}")
