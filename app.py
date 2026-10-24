
from pathlib import Path
import streamlit as st

from services.presentation_service import build_presentation
from services.quality_service import analyze_presentation
from services.generation_tracking_service import (
    build_tracked_presentation,
)
from services.quality_v2_service import (
    evaluate_presentation,
    Severity,
)

BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="SlideForge",
    page_icon="📊",
    layout="centered",
)

st.title("📊 SlideForge AI")

st.markdown(
    "Automatyczny generator prezentacji PowerPoint "
    "z wykorzystaniem Gemini i walidacji Pydantic."
)

# ==========================================
# INTERFEJS UŻYTKOWNIKA
# ==========================================

mode = st.radio(
    "Tryb generowania:",
    ["Gemini API", "Demo Mode"],
    horizontal=True
)

if mode == "Demo Mode":
    st.info(
        "Tryb demonstracyjny: 4 slajdy merytoryczne "
        "oraz slajd tytułowy, bez wywoływania API."
    )

topic = st.text_input(
    "Temat prezentacji:",
    placeholder="np. Wpływ AI na zarządzanie zasobami ludzkimi",
)

slides_count = st.slider(
    "Liczba slajdów merytorycznych:",
    min_value=1,
    max_value=25,
    value=5,
)

# ==========================================
# GENEROWANIE PREZENTACJI
# ==========================================

if st.button("Generuj prezentację", type="primary"):

    # Unieważniamy poprzedni wynik
    st.session_state.pop("presentation_file", None)
    st.session_state.pop("quality_warnings", None)
    st.session_state.pop("generated_filename", None)

    if mode == "Gemini API" and not topic.strip():
        st.error("Musisz podać temat prezentacji!")

    else:
        with st.spinner("Gemini generuje prezentację..."):
            try:
                output_path = (
                    BASE_DIR / "output" / "gotowa_prezentacja.pptx"
                )

                # 1. Generowanie prezentacji
                presentation = build_tracked_presentation(
                    mode="demo" if mode == "Demo Mode" else "gemini",
                    topic=topic.strip(),
                    slides_count=slides_count,
                    output_path=str(output_path),
                )

                # 2. Analiza jakości
                quality_report = evaluate_presentation(presentation)

                quality_warnings = [
                    (
                        f"Slajd {issue.slide_number} "
                        f"[{issue.severity.value}]: {issue.message}"
                    )
                    for issue in quality_report.issues
                    if issue.severity in (
                        Severity.WARNING,
                        Severity.ERROR,
                    )
                ]

                st.session_state["quality_score"] = quality_report.score
                st.session_state["quality_issues"] = quality_report.issues

                # 3. Zapis danych w sesji Streamlit
                st.session_state["presentation_file"] = (
                    output_path.read_bytes()
                )

                st.session_state["quality_warnings"] = quality_warnings

                st.session_state["generated_filename"] = (
                    "prezentacja_slideforge.pptx"
                )

            except Exception as exc:
                st.error(
                    f"Wystąpił błąd podczas generowania: {exc}"
                )

# ==========================================
# WYNIKI I KONTROLA JAKOŚCI
# ==========================================

if "presentation_file" in st.session_state:

    st.success("Prezentacja wygenerowana pomyślnie!")

    warnings = st.session_state.get(
        "quality_warnings", []
    )

    if warnings:
        with st.expander(
            f"⚠️ Uwagi dotyczące jakości ({len(warnings)})"
        ):
            for warning in warnings:
                st.warning(warning)
    else:
        st.success("Kontrola czytelności: bez uwag.")
if "quality_score" in st.session_state:
    st.metric(
        "Quality Score",
        f"{st.session_state['quality_score']}/100",
    )


    # ======================================
    # POBIERANIE PLIKU
    # ======================================

    st.download_button(
        label="📥 Pobierz prezentację (.pptx)",
        data=st.session_state["presentation_file"],
        file_name=st.session_state["generated_filename"],
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "presentationml.presentation"
        ),
    )
