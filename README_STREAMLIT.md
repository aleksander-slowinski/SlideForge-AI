# SlideForge v1.1 — Planned Generation page

## Scope

This patch creates a separate Streamlit page without altering `app.py` or Classic mode.
It requires the Sprint 10 Planner/Batch modules and the v1.1 A1/A2 checkpoint + retry services already installed.

## Installation

1. Ensure you are working on `feature/long-presentations` (`git branch --show-current`).
2. Unzip this patch into the **SlideForge project root** (merge `pages/`, `services/`, `tests/`).
3. Run `python -m pytest tests/test_planned_presentation_service.py -v` then `python -m pytest -q`.
4. Run `python -m streamlit run app.py`.
5. Open the new **Planned Generation** page in the Streamlit sidebar.
6. Use `output/presentation_plan.json` (the previous 12-slide plan), or upload a different plan JSON.
7. Check plan sections and checkpoint statuses **without making API requests**.
8. Click **Generuj / wznów prezentację** only when you want to actually call Gemini.

The page can be tested without Gemini through plan preview and the automated tests. With a 503 API outage, the UI displays a message and preserves valid checkpoints.

## Known scope limits

- Planned Generation SQL telemetry is **not integrated yet**. Classic logging is unchanged. Do not interpret missing SQL records as failure of this new page.
- No real complete 12-slide Gemini run has been confirmed due to repeated 503 responses. Automated tests use a fake generator.
- Checkpoint reuse requires the same plan, batch size, model, thinking level and pipeline revision.
- The renderer expects the standard SlideForge template: one added title slide plus the requested number of content slides.
- The default Streamlit multipage discovery works when `app.py` is the standard entrypoint and does not override navigation via `st.navigation()`.

## Next stage

Full end-to-end Gemini test when the model is reachable, followed by multi-call performance telemetry in SQL Server and Power BI.
