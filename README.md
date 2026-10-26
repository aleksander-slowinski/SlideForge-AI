# SlideForge AI

### AI-Powered Presentation Generation & Quality Analytics

SlideForge AI is a Python application that turns a user-defined topic into an editable PowerPoint presentation using Google's Gemini API. It combines **structured LLM generation, Pydantic validation, deterministic slide rendering, and quality checks** with an optional SQL Server and Power BI analytics layer.

The project was developed as a practical exploration of how generative AI can be integrated into a controlled document-production workflow, rather than used as an unconstrained text generator.

> **Project status:** v1.0 — stable presentation-generation workflow. The Presentation Planner and Batch Content Generator are experimental modules and are **not** part of the production Streamlit flow in this release.

## 📊 Project Overview

Creating a structured presentation usually involves several separate tasks: outlining the topic, drafting concise content, selecting layouts, formatting slides, and reviewing the result. Generative AI can accelerate content creation, but its output is not automatically suitable for a PowerPoint file: it can produce inconsistent structures, overcrowded slides, and unpredictable formatting.

SlideForge addresses this by separating **content generation** from **presentation rendering**. Gemini produces structured content, Pydantic verifies its shape, and Python renders it into a predefined PowerPoint template. A heuristic Quality Engine evaluates the resulting content, while telemetry makes the workflow measurable.

## 🎯 Business Value & Use Case

The application is designed for repeatable creation of academic and business-style presentations from a topic and a requested slide count.

- **Faster first drafts:** Generate an editable presentation instead of starting from an empty deck.
- **Consistent formatting:** Render content into reusable slide layouts with a shared visual language.
- **Controlled outputs:** Reject responses that violate the expected data structure or slide numbering.
- **Quality visibility:** Surface readability and content-density warnings before the file is used.
- **Operational observability:** Track generation success, execution time, model configuration, token usage, and quality metrics in SQL Server and Power BI.

This is a **portfolio / demonstration project**, not a substitute for editorial review or factual verification.

## ✨ Core Features

| Capability | Implementation |
|---|---|
| **Gemini Mode** | Generates a presentation from a topic using a configurable Gemini API model and thinking level. |
| **Demo Mode** | Builds a sample presentation without calling the Gemini API. |
| **11 slide layouts** | Layout-specific Pydantic models and editable PowerPoint shapes. |
| **Schema validation** | Enforces slide types, required fields, sequential numbering, and the requested slide count. |
| **PowerPoint export** | Creates a `.pptx` file using `python-pptx` and a reusable template. |
| **Quality Engine v2** | Assigns a heuristic score from 0 to 100 and reports issues by severity. |
| **SQL Server telemetry** | Records generation status, per-slide metrics, quality results, execution timings, and available API usage data. |
| **Power BI reporting** | Analyzes performance, reliability, slide layouts, errors, and quality trends. |

The main application supports **1–25 content slides**, with an additional title slide. Large decks may be more sensitive to model response size and latency; the full 25-slide range is not presented as a reliability guarantee.

### Supported layouts

| Layout | Purpose |
|---|---|
| `title_content` | Standard content with bullet points |
| `two_columns` | Parallel topics or grouped information |
| `comparison` | Side-by-side comparison |
| `conclusion` | Key findings and takeaways |
| `section_divider` | Section transition |
| `process_flow` | Ordered process or workflow |
| `timeline` | Chronological events or stages |
| `key_metrics` | Highlighted indicators and contextual notes |
| `case_study` | Problem, analysis, solution, and outcome |
| `quote_highlight` | Emphasized thesis or attributed quotation |
| `references` | Reference entries and source links |

## 🏗️ Technical Architecture

```text
User input (Streamlit)
         |
         v
   Gemini API / Demo Mode
         |
         v
 PresentationSchema (Pydantic)
         |
         +------------------------+
         |                        |
         v                        v
  Quality Engine v2       PowerPoint Renderer
  Score + issues          python-pptx + template
         |                        |
         |                        v
         |                  Editable .pptx
         |
         +------------+-----------+
                      |
                      v
            SQL Server Telemetry
                      |
                      v
               Power BI Reports
```

**Design principle:** Gemini determines the content; the application determines the data contract, rendering rules, and analytics. The quality score describes structural and readability heuristics — **it does not establish factual or legal correctness**.

### Main project modules

```text
app.py                         # Streamlit UI
prompt_builder.py              # LLM content instructions
models/schemas.py              # Presentation and slide schemas
services/llm_service.py        # Gemini integration
services/presentation_service.py
services/ppt_service.py        # PowerPoint orchestration
services/quality_v2_service.py # Layout-aware quality checks
services/generation_tracking_service.py
services/telemetry_service.py
services/db_service.py         # SQL Server connection
services/generation_metrics.py # Timing and token metrics
generators/                    # PowerPoint slide renderers
templates/template.pptx        # Editable presentation template
tests/                        # Automated tests
```

The repository also includes experimental `planner_service.py`, `batch_content_service.py`, and related plan schemas. These explore outline-first, multi-request generation for longer presentations but are deliberately kept outside the v1.0 user workflow.

## 🧠 Engineering Challenges & Design Decisions

### 1. Schema-first LLM generation

Rather than inserting unrestricted model text directly into slides, SlideForge validates the response against a Pydantic presentation model. Each of the 11 layouts has its own required content fields, reducing structural inconsistencies and enabling predictable downstream rendering.

### 2. Editable, deterministic PowerPoint rendering

The visual layer is implemented with `python-pptx` and a predefined template. Content is translated into native PowerPoint elements — including text boxes, cards, diagrams, and tables — instead of relying on screenshots of AI-generated slides. This keeps the exported deck editable.

### 3. Layout-aware Quality Engine

A single text-length threshold is insufficient for layouts with different visual capacities. Quality Engine v2 therefore evaluates content with **layout-specific heuristics** and returns an overall score, per-slide scores, and `INFO`, `WARNING`, or `ERROR` issues. The score helps identify likely presentation problems; it is not a semantic fact-checker.

### 4. Fault-tolerant telemetry

SQL Server is used for observability, not as a prerequisite for creating a PowerPoint file. Generation tracking attempts to record starts, successes, failures, quality issues, and model metrics, while database failures are handled separately so that an otherwise valid presentation can still be produced.

### 5. Measuring the actual AI workflow

The telemetry layer distinguishes the total generation duration from **Gemini API time, Pydantic validation time, and PPTX rendering time**. It also records the model, thinking level, and token metadata when the API supplies those values. This makes model comparisons more meaningful than looking at a single end-to-end average, especially because Demo Mode and Gemini Mode have very different execution profiles.

## 📈 SQL Server & Power BI Analytics

SlideForge stores analytical records in the `SlideForgeDB` database.

**Core tables**

| Table | Purpose |
|---|---|
| `dbo.GenerationRun` | Generation status, mode, duration, model configuration, and token metrics |
| `dbo.GeneratedSlide` | Slide-level layout and word-count metrics |
| `dbo.GenerationQuality` | Quality score and severity counts per generation |
| `dbo.QualityIssue` | Individual quality findings |

**Reporting views:** `dbo.vw_GenerationAnalytics`, `dbo.vw_SlideAnalytics`, and `dbo.vw_QualityIssueAnalytics`.

The Power BI report contains five analytical pages:

- **Overview:** generation volume and overall success indicators.
- **Generation Performance:** timing and AI usage metrics, including separate Demo and Gemini comparisons.
- **Slide Analysis:** layout distribution and content volume.
- **Error Analysis:** failed runs and reported error types.
- **Quality Analytics:** Quality Score trends and issue breakdowns.

The database connection is optional for producing PPTX files. SQL Server Express and the relevant ODBC driver are required for local telemetry; the database objects must be provisioned before analytics can be used. The Power BI report is a separate local reporting artifact, not an embedded Streamlit dashboard.

## 🧰 Tech Stack

| Layer | Technologies |
|---|---|
| Application | Python, Streamlit |
| Generative AI | Google Gemini API (`google-genai`) |
| Data contracts | Pydantic |
| Presentation rendering | `python-pptx` |
| Configuration | `python-dotenv` |
| Persistence | Microsoft SQL Server, `pyodbc`, Microsoft ODBC Driver |
| Analytics | Power BI Desktop, DAX |
| Testing | `pytest` |

## 🚀 Running Locally

The project was developed and tested in a **Windows / Python environment** with a local SQL Server Express instance. Other environments may require driver or path adjustments.

### 1. Clone and set up the environment

```powershell
git clone https://github.com/aleksander-slowinski/slideforge-ai.git
cd slideforge-ai
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation, you can run commands through `.\.venv\Scripts\python.exe` without activating it.

### 2. Configure the environment

Create a local `.env` file (or copy `.env.example` if available):

```dotenv
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=your_available_gemini_model
GEMINI_THINKING_LEVEL=medium

# Optional SQL Server telemetry
SQL_SERVER=.\SQLEXPRESS
SQL_DATABASE=SlideForgeDB
SQL_DRIVER=ODBC Driver 17 for SQL Server
```

Replace the example model name with a model available to your API key. **Never commit `.env` or API credentials.** API usage may incur costs independently of a consumer Gemini subscription.

### 3. Start the application

```powershell
python -m streamlit run app.py
```

Select **Demo Mode** to test the application without a Gemini request, or **Gemini API** to generate content from your own topic. Download the resulting editable PowerPoint file from Streamlit.

### 4. Run the test suite

```powershell
python -m pytest -v
```

Automated tests cover presentation schemas, layout rendering, quality rules, and generation tracking. The repository also contains separate development scripts for experimenting with presentation planning and batch generation.

## 🔐 Security & Limitations

- **Generated content requires human review.** Gemini may produce inaccurate statements, unsupported statistics, or fabricated references.
- **Quality Score is heuristic**, measuring selected structural and density rules rather than accuracy or visual perfection.
- **Topics are stored in generation telemetry** when SQL logging is available. Avoid entering confidential or personally identifiable information in the presentation topic.
- **Model availability, latency, usage limits, and API costs** are controlled by the Gemini API provider and can change over time.
- **Long presentations** may exceed practical model output or latency constraints even when their requested slide count passes schema validation.
- **Planner and Batch Generator are experimental**, not part of the supported v1.0 Streamlit workflow.

## 🛣️ Future Development

Potential post-v1.0 extensions include an editable presentation outline, reliable section-based generation for longer decks, persistence and resumption of completed batches, and source-grounded factual verification. These are **not required to run the released version**.

---

**SlideForge AI v1.0** — a portfolio project demonstrating practical integration of generative AI, structured data validation, document generation, software testing, SQL telemetry, and business intelligence.
