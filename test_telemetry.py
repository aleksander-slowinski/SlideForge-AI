
from pathlib import Path
from time import perf_counter

from services.demo_service import build_demo_presentation
from services.telemetry_service import (
    start_generation,
    finish_generation,
    fail_generation,
)
from services.db_service import get_connection


BASE_DIR = Path(__file__).resolve().parent

output_file = BASE_DIR / "output" / "telemetry_demo.pptx"

# Początek pomiaru
start_time = perf_counter()

# 1. Rejestracja rozpoczęcia generowania
run_id = start_generation(
    mode="demo",
    topic="[TEST] Demonstracja SlideForge",
    requested_slides=4,
)

print(f"Utworzono rekord RunID: {run_id}")

try:
    # 2. Generowanie prezentacji bez API
    presentation = build_demo_presentation(
        output_path=str(output_file)
    )

    duration_ms = int(
        (perf_counter() - start_time) * 1000
    )

    # 3. Zapis sukcesu i metryk
    finish_generation(
        run_id=run_id,
        presentation=presentation,
        duration_ms=duration_ms,
    )

    print("Status: SUCCESS")

except Exception:
    duration_ms = int(
        (perf_counter() - start_time) * 1000
    )

    fail_generation(
        run_id=run_id,
        duration_ms=duration_ms,
        error_code="TEST_ERROR",
    )

    raise


# 4. Odczyt zapisanych danych
connection = get_connection()

try:
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            Status,
            GeneratedSlides,
            DurationMs
        FROM dbo.GenerationRun
        WHERE RunID = ?
        """,
        run_id,
    )

    result = cursor.fetchone()

    print("\nDane z SQL Server:")
    print(f"Status: {result[0]}")
    print(f"Liczba slajdów: {result[1]}")
    print(f"Czas generowania: {result[2]} ms")

    cursor.execute(
        """
        SELECT
            SlideNumber,
            LayoutType,
            WordCount
        FROM dbo.GeneratedSlide
        WHERE RunID = ?
        ORDER BY SlideNumber
        """,
        run_id,
    )

    print("\nZapisane slajdy:")

    for row in cursor.fetchall():
        print(
            f"Slajd {row[0]} | "
            f"{row[1]} | "
            f"{row[2]} słów"
        )

finally:
    connection.close()
