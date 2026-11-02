# SlideForge AI

### AI-Powered Presentation Generation, Resumable Workflows & Quality Analytics

SlideForge AI is a Python and Streamlit project that converts a topic or a structured outline into an **editable PowerPoint presentation**. It combines Google's Gemini API, Pydantic schemas, deterministic `python-pptx` rendering, a heuristic Quality Engine, and optional SQL Server / Power BI analytics.

The central engineering goal is to make an LLM-driven document workflow **structured, inspectable, recoverable, and measurable**, rather than treating model output as a finished presentation.

> **Version status**
>
> - **v1.0 — stable (`main`, tag `v1.0.0`):** Classic generation, Demo Mode, 11 layouts, schema validation, PowerPoint export, Quality Engine v2, and SQL telemetry.
> - **v1.1 — in development (`feature/long-presentations`):** Planned Generation, resumable JSON checkpoints, bounded Gemini API retries, separate Streamlit page, and batch-level SQL telemetry.
> - **Not yet validated end-to-end against the live API:** completion of a full multi-batch presentation. Recent attempts were blocked by Gemini HTTP `503` responses. The v1.1 workflow has been tested with simulated dependencies; this is not a claim of production reliability.

## Project Overview

Presentation production involves more than drafting slide text: it requires a coherent outline, layout selection, predictable data structures, consistent formatting, and review. LLM output may be malformed, too long, inconsistent between slides, or interrupted by API errors.

SlideForge separates those concerns. **Gemini proposes structured content; Python validates, assembles, renders, and measures the result.** The planned-generation workflow extends this architecture to longer decks through smaller, independently validated batches that can be resumed after a failed request.

### Business Value

- **Faster first drafts:** Turn a topic or prepared outline into a downloadable, editable `.pptx` file.
- **Consistent presentation design:** Render native PowerPoint objects against a reusable template.
- **Controlled AI output:** Validate slide layouts, fields, slide counts, numbering, and plan compatibility.
- **Failure recovery:** Persist successful batches and avoid regenerating them after an interrupted run.
- **Operational visibility:** Record performance, failures, token metadata where available, and slide quality for analysis in Power BI.

SlideForge is a **portfolio and demonstration project**. Generated material still requires human fact-checking and visual review.

## Features and Validation Status

| Feature | Implementation | Status |
|---|---|---|
| Classic Generation | Topic-to-presentation workflow using Gemini and `PresentationSchema` | Stable v1.0 |
| Demo Mode | Offline sample deck, without Gemini requests | Stable v1.0 |
| 11 slide layouts | Layout-specific Pydantic models and editable PowerPoint shapes | Stable v1.0 |
| Quality Engine v2 | Per-slide structural/density rules, scores and severity-coded issues | Stable v1.0 |
| Presentation Planner | Generates a validated outline with sections, objectives and layout choices | Experimental; planner previously tested |
| Planned Generation UI | Dedicated Streamlit page for loading a plan and inspecting batch state | Implemented and UI-tested |
| Batch generation | Plan split into batches; output merged and checked against the plan | Unit/integration-tested with simulated responses |
| Resume checkpoints | Atomic JSON writes, content hashes and configuration fingerprints | Unit-tested; live multi-batch recovery still pending |
| API retry | Up to three attempts for HTTP `429` / `503`, with exponential backoff and jitter | Tested against real `503` responses |
| Planned SQL telemetry | Per-run and per-batch events, API call counts and checkpoint hits | SQL integration and synthetic failure scenario tested |
| Power BI analytics | Generation, slide composition, quality, failure and reliability reporting | Developed locally; report artifact may be separate from source repo |

### Supported Slide Layouts

| Layout | Intended use |
|---|---|
| `title_content` | Bullet-point content |
| `two_columns` | Parallel concepts or categories |
| `comparison` | Side-by-side analysis |
| `conclusion` | Main findings and recommendations |
| `section_divider` | Section transitions |
| `process_flow` | Ordered workflow steps |
| `timeline` | Events and milestones |
| `key_metrics` | Metrics with context and sources |
| `case_study` | Problem, analysis, solution and outcome |
| `quote_highlight` | Attributed quotation or key thesis |
| `references` | Source entries and URLs |

The schemas support **1–25 content slides**, plus a separately rendered title slide. This is a validation limit, **not** a guarantee that the Gemini API can generate every requested deck successfully.

## Architecture

### Classic Workflow — v1.0

```text
Streamlit: Topic + Slide Count
                |
                v
          Gemini API / Demo
                |
                v
     PresentationSchema (Pydantic)
                |
         +------+-------+
         |              |
         v              v
  Quality Engine v2   python-pptx + Template
         |              |
         +-------+------+ 
                 |
             PPTX + SQL Telemetry
                       |
                    Power BI
```

### Planned Workflow — v1.1 (Experimental)

```text
Validated PresentationPlanSchema (JSON)
                  |
         Streamlit Plan Preview
                  |
         Divide into Slide Batches
                  |
       +----------+------------+
       |                       |
  Checkpoint HIT          Missing Batch
       |                       |
  Revalidate JSON         Gemini API
       |                 (429/503 retry)
       |                       |
       |                Pydantic Validation
       |                       |
       |                Atomic JSON Checkpoint
       +-----------+-----------+
                   |
        Merge + Validate Full Plan
                   |
      Render + Verify Editable PPTX
                   |
             Quality Engine v2
                   |
          SQL Run / Batch Telemetry
                   |
                Power BI
```

**Important:** The v1.1 page currently **loads an existing JSON presentation plan**; it does not provide a complete plan-authoring interface. The planner is available separately through Python scripts.

## Engineering Decisions in v1.1

### 1. Resumable, validated batches

`services/resumable_batch_service.py` stores successfully generated batches in `output/checkpoints/`. A checkpoint is only saved **after schema and plan validation** and includes metadata and a SHA-256 content checksum.

The checkpoint directory is selected using a fingerprint of the plan and generation settings (including model, thinking level, batch size, instructions and pipeline revision). Reusing an incompatible or corrupted checkpoint is rejected instead of silently proceeding. Files are written through a temporary file and atomically replaced.

**Example:** If a 12-slide deck is split into batches of four and the third batch fails, the first two valid checkpoints can be reused on a subsequent attempt with the same configuration. A failed batch is not considered complete.

### 2. Bounded retries for transient failures

`services/api_retry_service.py` handles HTTP `429` and `503` with **three total attempts**, exponential backoff and a small random jitter. It does not retry validation problems, invalid configuration or unrelated errors. The internally owned Gemini client is configured to avoid duplicating retries already managed by the application.

Retries **mitigate transient failures**; they cannot guarantee model availability. A failed batch remains resumable from the last valid checkpoint.

### 3. Separation from the stable Classic path

Planned Generation runs on a separate Streamlit page (`pages/1_Planned_Generation.py`) and is orchestrated by dedicated service modules. The existing `app.py` and Classic generation path remain independent.

### 4. Validation of the final artifact

Before a Planned run is marked successful, the application validates the assembled presentation against the outline, renders a temporary PPTX, checks that it is readable and contains the expected number of slides, evaluates content quality, and only then promotes the completed file.

The Quality Engine checks formatting-oriented heuristics, including slide-specific density and length rules. **It does not verify factual accuracy or legal compliance.**

### 5. Observability without making SQL mandatory

The tracking layer tries to record each run and batch, but database write failures are handled separately. SQL Server is not required to render a PPTX. When token usage is unavailable — including some unsuccessful API calls — it is recorded as `NULL`, not inferred.

## SQL Server and Power BI

The optional analytics database is `SlideForgeDB`.

| Table | Grain / purpose |
|---|---|
| `dbo.GenerationRun` | One generation attempt; mode, strategy, status, duration, API metrics |
| `dbo.GeneratedSlide` | One generated content slide; layout and word count |
| `dbo.GenerationQuality` | Quality assessment for a successful generation |
| `dbo.QualityIssue` | Individual Quality Engine findings |
| `dbo.PlannedBatchExecution` | One batch within a Planned run; outcome, API calls, durations and optional tokens |

**Main reporting views:** `dbo.vw_GenerationAnalytics`, `dbo.vw_SlideAnalytics`, `dbo.vw_QualityIssueAnalytics`, and `dbo.vw_PlannedBatchAnalytics`.

The existing `GenerationMode` (`demo` / `gemini`) is distinct from the v1.1 **`GenerationStrategy`** (`classic` / `planned`). This prevents Demo runs from being mistaken for API-driven performance and supports future Classic-versus-Planned comparisons.

### Dashboard Topics

- **Overview** — run volume, status distribution and generation performance.
- **Generation Performance** — Gemini execution times, failure rates and run-level diagnostics.
- **Slide Analysis** — layout distribution, word counts and mode comparisons.
- **Error Analysis** — failed requests and error categories.
- **Quality Analytics** — heuristic quality scores and detected issues.
- **AI Reliability (v1.1)** — Planned batch outcomes, retry/API-call counts and checkpoint reuse.

The Power BI model should distinguish **synthetic test events** (marked with `[TEST]` and exposed as `IsTest`) from real run data. The v1.1 reliability page currently has limited observations; synthetic events demonstrate telemetry integration, **not measured production reliability**.

## Repository Structure

```text
app.py                                 # Stable Classic Streamlit entrypoint
pages/1_Planned_Generation.py          # Experimental v1.1 Streamlit page
models/schemas.py                      # Presentation / slide data contracts
models/planner_schemas.py              # Outline schemas
services/planner_service.py            # Outline generation
services/batch_content_service.py      # Batch prompts and content generation
services/resumable_batch_service.py    # Checkpoint store + resume orchestration
services/api_retry_service.py          # Bounded API retries
services/planned_presentation_service.py # Plan/PPTX orchestration
services/planned_tracking_service.py   # Run and batch measurement
services/planned_telemetry_service.py  # Planned SQL writes
services/telemetry_service.py          # Existing Classic SQL telemetry
services/quality_v2_service.py         # Quality Engine v2
services/ppt_service.py                # Editable PowerPoint rendering
generators/                            # Individual slide layout renderers
templates/template.pptx                # PowerPoint template
dev_test_planner.py                     # Creates a sample presentation plan (uses API)
dev_test_batches.py                     # Experimental batch test (uses API)
scripts/dev_test_planned_sql.py         # Synthetic SQL test without Gemini
tests/                                  # Automated tests
sql/                                    # SQL migrations / analytics objects
output/                                 # Local results + checkpoints (Git-ignored)
```

## Run Locally

The project was developed on Windows with Python 3.13. SQL Server Express is optional for generating presentations; it is needed for the database-backed analytics workflow.

### 1. Clone and choose a version

```powershell
git clone https://github.com/aleksander-slowinski/slideforge-ai.git
cd slideforge-ai

# v1.1 development branch, not the stable v1.0 release:
git switch feature/long-presentations

py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run commands with `.\.venv\Scripts\python.exe` directly. For automated tests, install `pytest` if not already present. For SQL telemetry, install `pyodbc` and the appropriate Microsoft ODBC Driver separately.

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in your local settings:

```dotenv
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=your_available_gemini_model
GEMINI_THINKING_LEVEL=medium

# Optional local SQL Server telemetry
SQL_SERVER=.\SQLEXPRESS
SQL_DATABASE=SlideForgeDB
SQL_DRIVER=ODBC Driver 17 for SQL Server
```

Never commit `.env`, API keys or local checkpoint contents. Model availability and API pricing depend on the provider and account configuration.

### 3. Start Streamlit

```powershell
python -m streamlit run app.py
```

- **Classic / Demo:** Use the original application workflow.
- **Planned Generation:** Open the separate page in the Streamlit navigation. Load `output/presentation_plan.json` or upload a valid plan JSON, inspect the sections and checkpoints, then explicitly start generation.

Browsing a plan or its checkpoint status does **not** call Gemini. Clicking **Generate / Resume** does.

### 4. Prepare a plan for Planned Generation

The development helper `dev_test_planner.py` creates a **specific demonstration outline** and writes it to `output/presentation_plan.json`. It **calls Gemini**, so it requires working API access:

```powershell
python dev_test_planner.py
```

Alternatively, provide a `PresentationPlanSchema`-compatible JSON file through the Planned Generation page. The schema includes `topic`, `presentation_type`, `slides_count`, `sections` and `slides` with slide objectives and content briefs.

For direct batch testing (also requires API access):

```powershell
python dev_test_batches.py --full
```

Completed checkpoint files remain in `output/checkpoints/` for compatible reruns.

### 5. Optional SQL telemetry

Set up the base `SlideForgeDB` tables, then apply the **corrected** Planned Generation schema migration (see `sql/` and project migration notes). Existing Classic records should remain intact; new Planned runs use `GenerationStrategy='planned'`.

For a SQL-only smoke test that does not call Gemini:

```powershell
python -m scripts.dev_test_planned_sql
```

This inserts a clearly labeled **synthetic failed run** for checking SQL and Power BI. Do not interpret it as a real API reliability measurement.

### 6. Automated tests

```powershell
python -m pip install pytest
python -m pytest -q
```

Tests include validation, presentation construction, checkpoint reuse/integrity, retry behavior and Planned orchestration with mocked dependencies. A passing offline suite does not replace a live multi-batch end-to-end test.

## Security and Limitations

- Generated slides may contain inaccuracies, unsupported statements or invented references; review before use.
- SQL telemetry records the presentation **topic**. Do not enter sensitive or personally identifying information in topics or documents intended for logging.
- `output/` contains local generation results and checkpoint JSON; it is excluded from version control. Checkpoints are recoverable intermediate artifacts, not encrypted or anonymized storage.
- LLM response latency, availability, rate limits and billing are outside the application's control.
- Checkpoint reuse depends on an unchanged compatible plan and configuration; incompatible/corrupt files stop the process rather than being silently reused.
- API retry counts reflect application/SDK calls as instrumented; token counts for unsuccessful requests may be unknown.
- Planned Generation currently consumes a plan created or supplied separately; it is not a complete no-code outline editor.
- Full live API validation for long decks and recovery after an actual mid-run outage remains pending.
- The SQL/Power BI layer is optional and has been developed in a local environment.

## Power BI Dashboard Gallery

SlideForge Analytics provides operational and technical insights
into presentation generation, AI performance, slide composition,
and workflow reliability.

### Operational Overview

![SlideForge Operational Overview](screenshots/overview.png)

### Generation Performance

![AI Generation Performance](screenshots/generation_performance.png)

### Additional Dashboards

- [Slide Analysis](screenshots/slide_analysis.png)
- [AI Reliability](screenshots/ai_reliability.png)

The dashboards are based on local SQL Server telemetry.
Synthetic test runs are distinguished from actual generation
results, and Planned Generation metrics remain preliminary
until full live API validation is completed.

## Roadmap

1. Complete a live 12-slide and then 20–25-slide end-to-end validation of Planned Generation when the API is available.
2. Verify mid-run checkpoint resume against real API interruption and compare it with mocked integration tests.
3. Expand the Power BI comparison of Classic versus Planned with more real observations; publish sanitized dashboard screenshots.
4. Consider a UI flow for creating and editing presentation plans without a separate development script.

---

**SlideForge AI** demonstrates schema-first generative AI, native document rendering, recoverable batch execution, controlled API retries, SQL observability and Business Intelligence — with a stable v1.0 baseline and an experimental v1.1 extension.
