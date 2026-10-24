import json
from models.schemas import PresentationSchema

def get_system_prompt() -> str:
    # Wyciągamy surowy schemat JSON bezpośrednio z naszego modelu Pydantic
    schema_dict = PresentationSchema.model_json_schema()
    
    # Zamieniamy słownik na ładnie sformatowany tekst JSON
    schema_json = json.dumps(schema_dict, indent=2, ensure_ascii=False)
    
    # Budujemy prompt systemowy wstrzykując w niego nasz schemat
    system_prompt = f"""Jesteś ekspertem od tworzenia profesjonalnych prezentacji biznesowych i akademickich.
Twoim zadaniem jest wygenerowanie struktury prezentacji na podany przez użytkownika temat.

MUSISZ zwrócić odpowiedź jako czysty, poprawny kod JSON.
Zwrócony JSON musi absolutnie i rygorystycznie odpowiadać poniższemu schematowi (JSON Schema):

{schema_json}

ZASADY DODATKOWE:
1. Zawsze używaj języka polskiego.
2. Zadbaj o logikę struktury: zadeklarowana wartość 'slides_count' musi dokładnie odpowiadać fizycznej liczbie elementów w tablicy 'slides'.
3. Zawsze zachowuj ciągłość numeracji w 'slide_number' (1, 2, 3...).
4. W polu 'speaker_notes' umieszczaj konkretne, zwięzłe wskazówki dla osoby prowadzącej prezentację.
5. Nie dodawaj żadnego tekstu przed ani po JSON-ie (żadnych wstępów, żadnych bloków kodu typu ```json). Masz wypluć sam, czysty JSON."""
    
    return system_prompt


def build_user_prompt(topic: str, slides_count: int) -> str:
    topic = topic.strip()

    if not topic:
        raise ValueError("Temat prezentacji nie może być pusty.")

    return f"""
Przygotuj prezentację akademicką w języku polskim.

TEMAT:
{topic}

WYMAGANIA:
1. Wygeneruj dokładnie {slides_count} slajdów merytorycznych.
2. Numeruj slajdy od 1 do {slides_count}.
3. Ustaw slides_count na {slides_count}.
4. Nie umieszczaj slajdu tytułowego w liście slides.
   Jest on tworzony automatycznie przez Python.
5. Używaj tylko obsługiwanych layoutów:
   - title_content
   - two_columns
   - comparison
   - conclusion
   - section_divider
   - process_flow
   - timeline

NOWE DOSTĘPNE LAYOUTY:

section_divider:
- Służy do oddzielania rozdziałów prezentacji.
- Pola: slide_number, layout, title, subtitle, speaker_notes.
- Nie używaj go zbyt często.
- W prezentacjach krótszych niż 8 slajdów zwykle nie jest potrzebny.

process_flow:
- Przedstawia procedurę składającą się z 3–5 kolejnych etapów.
- Pola: slide_number, layout, title, steps, speaker_notes.
- steps zawiera obiekty z polami heading i description.
- Stosuj tylko wtedy, gdy etapy tworzą rzeczywisty proces.

timeline:
- Przedstawia chronologię obejmującą 3–5 wydarzeń.
- Pola: slide_number, layout, title, events, speaker_notes.
- events zawiera obiekty z polami period, heading i description.
- Nie wymyślaj dat ani wydarzeń.
- Gdy brak konkretnych dat, można użyć oznaczeń etapów.

DOBÓR LAYOUTÓW:
- Wybieraj layout na podstawie rodzaju informacji.
- Nie stosuj jednego układu na kolejnych wielu slajdach.
- Zachowuj logiczną strukturę prezentacji.
- Unikaj przeładowania tekstem.
- Łączna liczba slajdów merytorycznych musi
  odpowiadać slides_count.

  
NOWE LAYOUTY:

key_metrics:
- Pola: slide_number, layout, title, metrics, speaker_notes.
- metrics: 2–4 obiekty zawierające label, value,
  description i opcjonalne source.
- Stosuj tylko dla rzeczywistych, uzasadnionych danych.
- Nie wymyślaj wartości liczbowych ani statystyk.
- Jeśli nie masz wiarygodnych danych, wybierz inny layout.

case_study:
- Pola: slide_number, layout, title,
  problem, analysis, solution, outcome, speaker_notes.
- Stosuj do konkretnych przypadków i analiz.
- Jeśli opisujesz wymyślony scenariusz edukacyjny,
  zaznacz w tytule, że jest hipotetyczny.

quote_highlight:
- Pola: slide_number, layout, title,
  kind, statement, attribution, speaker_notes.
- kind = "thesis" dla własnej tezy lub podsumowania.
- kind = "quotation" tylko dla rzeczywistego,
  potwierdzonego cytatu z podanym źródłem.
- Nie przypisuj wymyślonych cytatów znanym osobom.

references:
- Pola: slide_number, layout, title,
  references, speaker_notes.
- Każda pozycja zawiera citation i opcjonalne url.
- Maksymalnie 5 pozycji na jednym slajdzie.
- Uwzględniaj wyłącznie źródła dostarczone
  przez użytkownika lub rzeczywiście zweryfikowane.
- Nigdy nie wymyślaj publikacji, autorów, DOI i URL.
- Jeśli brak źródeł, nie twórz tego layoutu.

DOBÓR LAYOUTÓW:
- Wybieraj układy na podstawie rodzaju informacji.
- Nie stosuj Key Metrics bez wiarygodnych liczb.
- Nie stosuj References bez rzeczywistych źródeł.
- Unikaj nadmiernego powtarzania layoutów.
- Zachowaj spójność narracji całej prezentacji.


6. Dobieraj layout do rodzaju prezentowanych informacji.
7. Do każdego slajdu przygotuj speaker_notes.
8. Zachowaj logiczną kolejność zagadnień.
9. Unikaj niepotrzebnego powtarzania treści.
10. Nie wymyślaj statystyk ani źródeł.

Zwróć strukturę JSON zgodną z wymaganym schematem.
"""