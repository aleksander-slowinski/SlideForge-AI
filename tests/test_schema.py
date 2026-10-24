from models.schemas import PresentationSchema

# POPRAWNY JSON
valid_presentation = {
    "title": "Podstawy prawa zobowiązań",
    "topic": "Prawo cywilne – zobowiązania",
    "language": "pl",
    "slides_count": 3,
    "slides": [
        {
            "slide_number": 1,
            "title": "Czym jest zobowiązanie?",
            "layout": "title_content",
            "bullet_points": [
                "Stosunek prawny między wierzycielem a dłużnikiem",
                "Obowiązek określonego świadczenia",
            ],
            "speaker_notes": "Wyjaśnij podstawową definicję zobowiązania.",
        },
        {
            "slide_number": 2,
            "title": "Strony zobowiązania",
            "layout": "two_columns",
            "columns": [
                {
                    "title": "Wierzyciel",
                    "bullet_points": ["Ma prawo żądać świadczenia"],
                },
                {
                    "title": "Dłużnik",
                    "bullet_points": ["Jest zobowiązany do świadczenia"],
                },
            ],
            "speaker_notes": "Porównaj pozycję wierzyciela i dłużnika.",
        },
        {
            "slide_number": 3,
            "title": "Najważniejsze wnioski",
            "layout": "conclusion",
            "key_points": [
                "Zobowiązanie tworzy więź prawną między stronami",
            ],
            "speaker_notes": "Podsumuj najważniejsze informacje.",
        },
    ],
}

print("--- TEST 1: POPRAWNE DANE ---")
try:
    presentation = PresentationSchema.model_validate(valid_presentation)
    print("Walidacja zakończona sukcesem!")
except Exception as e:
    print(f"Błąd walidacji: {e}")

print("\n--- TEST 2: BŁĘDNA LICZBA SLAJDÓW ---")
invalid_presentation_1 = valid_presentation.copy()
invalid_presentation_1["slides_count"] = 4
try:
    PresentationSchema.model_validate(invalid_presentation_1)
except Exception as e:
    print("Oczekiwany błąd przechwycony:\n", e)

print("\n--- TEST 3: BŁĘDNA NUMERACJA SLAJDÓW ---")
invalid_presentation_2 = valid_presentation.copy()
invalid_presentation_2["slides_count"] = 3
invalid_presentation_2["slides"][2]["slide_number"] = 4 
try:
    PresentationSchema.model_validate(invalid_presentation_2)
except Exception as e:
    print("Oczekiwany błąd przechwycony:\n", e)