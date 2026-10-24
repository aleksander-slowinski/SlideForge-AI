
from pathlib import Path

from services.planner_service import (
    generate_presentation_plan,
)


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


plan = generate_presentation_plan(
    topic=(
        "Prawno-administracyjne aspekty zarządzania "
        "zgodnością (compliance) w przedsiębiorstwie "
        "z wykorzystaniem narzędzi "
        "Business Intelligence"
    ),
    slides_count=12,
    presentation_type="academic",
)


print("\n=== PRESENTATION OUTLINE ===")

for section in plan.sections:
    print(
        f"\nSEKCJA {section.section_number}: "
        f"{section.title}"
    )
    print(f"Cel: {section.goal}")

    slides = [
        slide for slide in plan.slides
        if slide.section_number == section.section_number
    ]

    for slide in slides:
        print(
            f"  {slide.slide_number:02d}. "
            f"{slide.title} "
            f"[{slide.layout.value}]"
        )

        for point in slide.content_brief:
            print(f"      - {point}")


output_file = OUTPUT_DIR / "presentation_plan.json"

output_file.write_text(
    plan.model_dump_json(indent=2),
    encoding="utf-8",
)

print(f"\nZapisano plan: {output_file}")
