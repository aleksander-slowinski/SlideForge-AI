
import json
import logging
import os

from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from pydantic import ValidationError

from models.planner_schemas import (
    PresentationPlanSchema,
    PlannedSlide,
)
from models.schemas import PresentationSchema
from prompt_builder import get_system_prompt


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger(__name__)


BATCH_RULES = """
TRYB GENEROWANIA PARTII SLIDEFORGE:

- Zwróć wyłącznie poprawny obiekt JSON
  zgodny z istniejącym PresentationSchema.

- Wygeneruj WYŁĄCZNIE slajdy wskazane
  w BIEŻĄCEJ PARTII.

- Używaj LOKALNEJ numeracji slajdów
  od 1 do liczby slajdów w partii.

- Zachowaj dokładnie tytuły oraz layouty
  wskazane w bieżącej partii.

- Wykorzystaj objective oraz content_brief
  jako wytyczne do napisania treści.

- Nie kopiuj content_brief dosłownie.
  Rozwiń zagadnienia w odpowiednią
  treść prezentacyjną.

- Cały konspekt służy do zachowania
  kontekstu i logicznej narracji.

- Nie powtarzaj zagadnień szczegółowo
  omówionych we wcześniejszych slajdach.

- Zachowaj komplet wymaganych pól
  specyficznych dla każdego layoutu.

- Pisz po polsku, zwięźle i rzeczowo.
- Unikaj przeładowania slajdów tekstem.
- Uwzględniaj notatki prelegenta.


OGRANICZENIA DŁUGOŚCI:

- Wszystkie pola tekstowe muszą spełniać
  ograniczenia schematu Pydantic.

- Dla layoutu timeline:
  * period: maksymalnie 25 znaków
  * heading: maksymalnie 40 znaków
  * description: maksymalnie 90 znaków

- Dla layoutu process_flow:
  * heading: maksymalnie 40 znaków
  * description: maksymalnie 100 znaków

- Preferuj krótkie, kompletne zdania.
- Nie przekraczaj limitów długości pól.
- Dodatkowe wyjaśnienia umieszczaj
  w speaker_notes.


RZETELNOŚĆ:
- Nie wymyślaj statystyk ani źródeł.
- Nie fabrykuj cytatów i wyników badań.
- Przykłady hipotetyczne oznaczaj
  jako hipotetyczne.
- Nie przedstawiaj warunkowych
  obowiązków prawnych jako bezwzględnych.
- Rozróżniaj tezy, przepisy i postulaty.

Nie dodawaj Markdown ani komentarzy
wokół wynikowego JSON.
"""


def split_plan_into_batches(
    plan: PresentationPlanSchema,
    batch_size: int = 4,
) -> list[list[PlannedSlide]]:
    """Dzieli plan na kolejne partie slajdów."""

    if (
        not isinstance(batch_size, int)
        or isinstance(batch_size, bool)
        or not 1 <= batch_size <= 10
    ):
        raise ValueError(
            "batch_size musi być liczbą "
            "całkowitą od 1 do 10."
        )

    return [
        plan.slides[i:i + batch_size]
        for i in range(0, len(plan.slides), batch_size)
    ]


def _build_batch_prompt(
    plan: PresentationPlanSchema,
    batch: Sequence[PlannedSlide],
    previous_slides: Sequence,
    presentation_title: str | None,
) -> str:
    """Buduje kontekst dla pojedynczej partii."""

    section_names = {
        section.section_number: section.title
        for section in plan.sections
    }

    # Cały plan: zachowanie kontekstu.
    outline = [
        {
            "nr": slide.slide_number,
            "tytul": slide.title,
            "layout": slide.layout.value,
            "sekcja": section_names[
                slide.section_number
            ],
        }
        for slide in plan.slides
    ]

    # Tylko slajdy do wygenerowania.
    tasks = [
        {
            "lokalny_numer": local_number,
            "globalny_numer": slide.slide_number,
            "tytul": slide.title,
            "layout": slide.layout.value,
            "cel": slide.objective,
            "content_brief": slide.content_brief,
        }
        for local_number, slide in enumerate(
            batch, start=1
        )
    ]

    # Skrócony kontekst ostatnich czterech
    # wygenerowanych slajdów.
    context = [
        {
            "globalny_numer": slide.slide_number,
            "tytul": slide.title,
            "tresc_skrocona": json.dumps(
                slide.model_dump(mode="json"),
                ensure_ascii=False,
            )[:500],
        }
        for slide in previous_slides[-4:]
    ]

    requested_title = (
        presentation_title
        if presentation_title is not None
        else (
            "Wymyśl jeden zwięzły tytuł "
            "prezentacji, maksymalnie 150 znaków."
        )
    )

    return (
        f"TEMAT: {plan.topic}\n"
        f"RODZAJ: {plan.presentation_type}\n"
        f"WYMAGANY title: {requested_title}\n"
        f"WYMAGANY topic (dokładnie): "
        f"{plan.topic}\n"
        "WYMAGANY language: pl\n"
        f"WYMAGANY slides_count: {len(batch)}\n"
        f"LOKALNA NUMERACJA: 1..{len(batch)}\n\n"

        "CAŁY KONSPEKT (TYLKO KONTEKST):\n"
        f"{json.dumps(outline, ensure_ascii=False)}\n\n"

        "WCZEŚNIEJ WYGENEROWANE SLAJDY "
        "(TYLKO KONTEKST):\n"
        f"{json.dumps(context, ensure_ascii=False)}\n\n"

        "BIEŻĄCA PARTIA — GENERUJ TYLKO "
        "PONIŻSZE SLAJDY:\n"
        f"{json.dumps(tasks, ensure_ascii=False)}\n\n"

        "Wynikowy JSON musi zawierać pola: "
        "title, topic, language, slides_count, "
        "slides.\n"

        "Każdy slajd musi zawierać: "
        "slide_number (LOKALNY), title, layout "
        "oraz pola właściwe dla layoutu.\n"

        "speaker_notes mogą zawierać dodatkowy "
        "kontekst dla prowadzącego.\n"

        "Nie kopiuj do wynikowych slajdów "
        "pól objective ani content_brief."
    )

def validate_or_repair_batch_response(
    raw_json: str,
    *,
    client,
    model_name: str,
    config,
) -> PresentationSchema:
    """Validate JSON and attempt one targeted repair."""

    try:
        return PresentationSchema.model_validate_json(raw_json)

    except ValidationError as exc:
        issues = [
            {
                "field": ".".join(
                    str(part) for part in error["loc"]
                ),
                "message": error["msg"],
            }
            for error in exc.errors()
        ]

        logger.warning(
            "Gemini JSON validation failed: %s",
            issues,
        )

        repair_prompt = (
            "Popraw poniższy JSON, aby spełniał "
            "wymagania schematu prezentacji.\n\n"
            "ZASADY:\n"
            "- Popraw wyłącznie błędne pola.\n"
            "- Zachowaj znaczenie merytoryczne.\n"
            "- Zachowaj tytuły, layouty, numerację "
            "i liczbę slajdów.\n"
            "- Zachowaj pozostałe pola bez zmian.\n"
            "- Nie ucinaj zdań w połowie.\n"
            "- Zwróć wyłącznie poprawny JSON.\n\n"
            "BŁĘDY WALIDACJI:\n"
            f"{json.dumps(issues, ensure_ascii=False)}\n\n"
            "ORYGINALNY JSON:\n"
            f"{raw_json}"
        )

        try:
            repaired = client.models.generate_content(
                model=model_name,
                contents=repair_prompt,
                config=config,
            )
        except errors.APIError as api_exc:
            raise RuntimeError(
                "Gemini Content Repair: "
                f"błąd API ({api_exc.code})."
            ) from api_exc

        if not repaired.text:
            raise ValueError(
                "Gemini Content Repair zwrócił pustą odpowiedź."
            )

        return PresentationSchema.model_validate_json(
            repaired.text
        )


def generate_batch(
    plan: PresentationPlanSchema,
    batch: Sequence[PlannedSlide],
    client,
    previous_slides: Sequence = (),
    presentation_title: str | None = None,
) -> PresentationSchema:
    """
    Generuje i waliduje pojedynczą partię.

    Wynik posiada LOKALNĄ numerację 1..N.
    Funkcja nie zapisuje pliku PPTX.
    """

    if not batch:
        raise ValueError(
            "Nie można generować pustej partii."
        )

    expected_numbers = list(
        range(
            batch[0].slide_number,
            batch[0].slide_number + len(batch),
        )
    )

    if [
        slide.slide_number for slide in batch
    ] != expected_numbers:
        raise ValueError(
            "Partia musi zawierać kolejne slajdy."
        )

    if any(
        plan.slides[slide.slide_number - 1] != slide
        for slide in batch
    ):
        raise ValueError(
            "Partia musi pochodzić "
            "z przekazanego planu."
        )

    model_name = os.getenv(
        "GEMINI_MODEL", "gemini-3.8-flash"
    ).strip()

    thinking_level = os.getenv(
        "GEMINI_THINKING_LEVEL", "medium"
    ).strip().lower()

    if thinking_level not in (
        "low", "medium", "high"
    ):
        raise ValueError(
            "Nieprawidłowy GEMINI_THINKING_LEVEL."
        )

    config = types.GenerateContentConfig(
        system_instruction=(
            get_system_prompt()
            + "\n"
            + BATCH_RULES
        ),
        response_mime_type="application/json",
        max_output_tokens=16000,
        thinking_config=types.ThinkingConfig(
            thinking_level=thinking_level,
        ),
    )

    prompt = _build_batch_prompt(
        plan=plan,
        batch=batch,
        previous_slides=previous_slides,
        presentation_title=presentation_title,
    )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )

    except errors.APIError as exc:
        raise RuntimeError(
            "Gemini Batch Generator: "
            f"błąd API ({exc.code})."
        ) from exc

    if not response.text:
        raise ValueError(
            "Gemini zwrócił pustą odpowiedź "
            f"dla slajdów {expected_numbers}."
        )

    # Pierwsza bariera walidacji:
    # kompletna struktura każdego layoutu.
    result = validate_or_repair_batch_response(
    response.text,
    client=client,
    model_name=model_name,
    config=config,
)


    if result.slides_count != len(batch):
        raise ValueError(
            "Gemini zwrócił nieprawidłową "
            "liczbę slajdów w partii."
        )

    if result.topic != plan.topic:
        raise ValueError(
            "Gemini zmienił temat prezentacji."
        )

    if (
        presentation_title is not None
        and result.title != presentation_title
    ):
        raise ValueError(
            "Gemini zmienił tytuł prezentacji "
            "pomiędzy partiami."
        )

    # Druga bariera:
    # zgodność z wcześniej zatwierdzonym planem.
    for local_number, (
        actual, expected
    ) in enumerate(zip(result.slides, batch), start=1):

        if actual.slide_number != local_number:
            raise ValueError(
                "Nieprawidłowa numeracja lokalna."
            )

        if actual.layout != expected.layout:
            raise ValueError(
                "Niezgodny layout slajdu "
                f"globalnego {expected.slide_number}."
            )

        if actual.title != expected.title:
            raise ValueError(
                "Niezgodny tytuł slajdu "
                f"globalnego {expected.slide_number}."
            )

    return result


def generate_content_from_plan(
    plan: PresentationPlanSchema,
    batch_size: int = 4,
    client=None,
) -> PresentationSchema:
    """
    Generuje wszystkie partie, scala je
    i ponownie waliduje pełną prezentację.
    """

    batches = split_plan_into_batches(
        plan,
        batch_size=batch_size,
    )

    owns_client = client is None

    if owns_client:
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "Brak GEMINI_API_KEY w pliku .env."
            )

        client = genai.Client(api_key=api_key)

    collected = []
    presentation_title = None

    try:
        for batch_index, batch in enumerate(
            batches, start=1
        ):
            logger.info(
                "Batch %s/%s: slajdy %s-%s",
                batch_index,
                len(batches),
                batch[0].slide_number,
                batch[-1].slide_number,
            )

            batch_result = generate_batch(
                plan=plan,
                batch=batch,
                client=client,
                previous_slides=collected,
                presentation_title=presentation_title,
            )

            if presentation_title is None:
                presentation_title = batch_result.title

            # Zamiana numerów lokalnych na globalne.
            for actual, expected in zip(
                batch_result.slides, batch
            ):
                global_slide = actual.model_copy(
                    update={
                        "slide_number": (
                            expected.slide_number
                        )
                    }
                )

                collected.append(global_slide)

    finally:
        if owns_client:
            client.close()

    # Ostateczna walidacja kompletu.
    return PresentationSchema.model_validate(
        {
            "title": presentation_title,
            "topic": plan.topic,
            "language": "pl",
            "slides_count": plan.slides_count,
            "slides": [
                slide.model_dump(mode="json")
                for slide in collected
            ],
        }
    )
