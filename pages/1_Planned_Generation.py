"""Separate Streamlit page for experimental Planned Generation (v1.1).

Streamlit discovers files in pages/ automatically when app.py is the entrypoint.
This page DOES NOT modify Classic mode or the existing SQL telemetry.
"""
from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st
from pydantic import ValidationError

from services.api_retry_service import api_error_status
from services.planned_presentation_service import (
    checkpoint_overview,
    load_presentation_plan,
)
from services.resumable_batch_service import CheckpointError
from services.planned_tracking_service import build_tracked_planned_artifact


logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "output"
DEFAULT_PLAN = OUTPUT_DIR / "presentation_plan.json"
CHECKPOINT_ROOT = OUTPUT_DIR / "checkpoints"

st.set_page_config(page_title="SlideForge — Planned Generation", page_icon="🧩", layout="wide")
st.title("🧩 Planned Generation — v1.1")
st.caption("Eksperymentalny tryb generowania partiami. Classic Mode pozostaje bez zmian.")

source = st.radio(
    "Skąd wczytać konspekt?",
    ["Zapisany plan w output/", "Wgraj plik JSON"],
    horizontal=True,
)
raw_plan = None
if source == "Zapisany plan w output/":
    if DEFAULT_PLAN.exists():
        raw_plan = DEFAULT_PLAN.read_bytes()
        st.caption("Źródło: output/presentation_plan.json")
    else:
        st.info("Nie znaleziono output/presentation_plan.json. Wybierz wgranie JSON.")
else:
    uploaded = st.file_uploader("Presentation Plan (.json)", type=["json"])
    if uploaded is not None:
        raw_plan = uploaded.getvalue()

if raw_plan is None:
    st.stop()

try:
    plan = load_presentation_plan(raw_plan)
except (ValidationError, ValueError, UnicodeDecodeError) as exc:
    st.error("Nie udało się zwalidować konspektu. Sprawdź format PresentationPlanSchema.")
    st.stop()

batch_size = st.selectbox("Liczba slajdów w partii", [2, 3, 4, 5], index=2)

try:
    fingerprint, checkpoint_rows = checkpoint_overview(
        plan, checkpoint_root=CHECKPOINT_ROOT, batch_size=batch_size,
    )
except CheckpointError:
    st.error(
        "Wykryto nieprawidłowy checkpoint. Generowanie zostało zablokowane. "
        "Sprawdź pliki w output/checkpoints/ — nie są automatycznie nadpisywane."
    )
    st.stop()

st.subheader("Konspekt")
a, b, c = st.columns(3)
a.metric("Slajdy merytoryczne", plan.slides_count)
b.metric("Sekcje", len(plan.sections))
c.metric("Partie", len(checkpoint_rows))

for section in plan.sections:
    slides = [s for s in plan.slides if s.section_number == section.section_number]
    with st.expander(f"Sekcja {section.section_number}: {section.title} ({len(slides)} slajdów)"):
        st.caption(section.goal)
        st.dataframe(
            [{"Nr": s.slide_number, "Tytuł": s.title, "Layout": s.layout.value}
             for s in slides],
            use_container_width=True, hide_index=True,
        )

st.subheader("Stan checkpointów")
st.dataframe(checkpoint_rows, use_container_width=True, hide_index=True)
finished = sum(item["Status"] == "Checkpoint HIT" for item in checkpoint_rows)
st.caption(f"Ukończone partie: {finished}/{len(checkpoint_rows)}. Zmiana modelu lub planu tworzy nowy zestaw checkpointów.")
st.info(
    "Przy niedostępności Gemini (HTTP 503) operacja może zakończyć się błędem. "
    "Poprawnie zapisane partie zostają na dysku i można później wznowić generowanie."
)

if st.button("Generuj / wznów prezentację", type="primary"):
    # Never show a previous result for a newly started run.
    st.session_state.pop("planned_artifact", None)
    try:
        with st.spinner("Generowanie brakujących partii i tworzenie PPTX..."):
            artifact = build_tracked_planned_artifact(
                plan,
                output_dir=OUTPUT_DIR,
                checkpoint_root=CHECKPOINT_ROOT,
                batch_size=batch_size,
            )
        st.session_state["planned_artifact"] = artifact
        st.success("Prezentacja została wygenerowana i zwalidowana.")
        st.rerun()
    except CheckpointError:
        st.error("Uszkodzony lub niezgodny checkpoint. Sprawdź katalog output/checkpoints/.")
    except Exception as exc:
        status = api_error_status(exc)
        if status in (429, 503):
            st.warning(f"Gemini API zwróciło HTTP {status}. Zachowano ukończone checkpointy; spróbuj wznowić później.")
        else:
            st.error(
                f"Nie udało się wygenerować prezentacji ({type(exc).__name__}). "
                "Szczegóły techniczne znajdują się w lokalnym terminalu."
            )
        logger.exception("Planned Generation failed")

artifact = st.session_state.get("planned_artifact")
if artifact is not None and artifact.checkpoint_fingerprint == fingerprint:
    st.subheader("Gotowa prezentacja")
    report = artifact.quality_report
    x, y, z = st.columns(3)
    x.metric("Quality Score", f"{report.score}/100")
    y.metric("Warnings", report.warning_count)
    z.metric("Errors", report.error_count)
    st.download_button(
        "📥 Pobierz prezentację (.pptx)",
        data=artifact.pptx_data,
        file_name=artifact.filename,
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        type="primary",
    )

st.caption("Planned Generation zapisuje telemetrię SQL, jeśli serwer jest dostępny. Awaria bazy nie blokuje PPTX.")
