
import logging
import os
import sys

from pathlib import Path

from dotenv import load_dotenv
from google import genai

from models.planner_schemas import PresentationPlanSchema
from services.batch_content_service import (
    generate_batch,
    generate_content_from_plan,
)


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)

# Domyślnie test jednej partii.
# Argument --full uruchamia wszystkie partie.
full_generation = "--full" in sys.argv


# ==========================================
# LOAD PRESENTATION PLAN
# ==========================================

plan_path = OUTPUT_DIR / "presentation_plan.json"

plan = PresentationPlanSchema.model_validate_json(
    plan_path.read_text(encoding="utf-8")
)

print(
    f"\nWczytano konspekt: "
    f"{plan.slides_count} slajdów",
    flush=True,
)


# ==========================================
# GEMINI CLIENT
# ==========================================

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Brak GEMINI_API_KEY")

client = genai.Client(api_key=api_key)


try:
    if not full_generation:

        # ==================================
        # TEST: FIRST BATCH
        # ==================================

        print(
            "\nGenerowanie pierwszej partii: "
            "slajdy 1-4...",
            flush=True,
        )

        presentation = generate_batch(
            plan=plan,
            batch=plan.slides[:4],
            client=client,
        )

        output_file = (
            OUTPUT_DIR / "batch_1_content.json"
        )

    else:

        # ==================================
        # FULL PRESENTATION
        # ==================================

        print(
            "\nGenerowanie całej prezentacji "
            "w partiach...",
            flush=True,
        )

        presentation = generate_content_from_plan(
            plan=plan,
            batch_size=4,
            client=client,
        )

        output_file = (
            OUTPUT_DIR / "presentation_content.json"
        )

finally:
    client.close()


# ==========================================
# SAVE JSON
# ==========================================

output_file.write_text(
    presentation.model_dump_json(indent=2),
    encoding="utf-8",
)

print(
    f"\nZapisano: {output_file}",
    flush=True,
)

print(
    f"Liczba slajdów: "
    f"{presentation.slides_count}"
)

for slide in presentation.slides:
    print(
        f"{slide.slide_number:02d}. "
        f"{slide.title} "
        f"[{slide.layout.value}]"
    )


# ==========================================
# OPTIONAL PPTX FOR FULL GENERATION
# ==========================================

if full_generation:
    from services.ppt_service import (
        create_presentation,
    )

    from services.quality_v2_service import (
        evaluate_presentation,
    )

    pptx_path = (
        OUTPUT_DIR / "batch_presentation.pptx"
    )

    create_presentation(
        data=presentation,
        filename=str(pptx_path),
    )

    quality_report = evaluate_presentation(
        presentation
    )

    print(
        f"\nQuality Score: "
        f"{quality_report.score}/100"
    )

    print(
        f"PPTX zapisany: {pptx_path}"
    )