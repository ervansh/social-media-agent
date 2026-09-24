# Social Media Agent

Agentic social media content generation system built around a multi-stage content pipeline. The project researches a topic, generates content ideas, selects a winning idea, creates platform-specific drafts, validates them, and produces creative asset briefs for downstream publishing or image generation.

## Overview

This repository contains a Python-based content engine that combines:

- LLM-driven research and idea generation
- Content strategy and master storytelling
- Grounding checks against source material
- Platform-specific adaptation for YouTube, Instagram, and X
- Quality validation and retry loops
- Creative asset planning and optional image generation
- Persistence of each run and artifact state
- CLI execution and a Streamlit dashboard

The system is designed for iterative, stateful content production where each run can be resumed and inspected from a local SQLite database.

## Core Features

### Research and ideation
- Searches the web for source material using the configured search provider
- Produces a structured research brief summarizing findings and sources
- Generates multiple content ideas with recommended platforms and rationale
- Saves each artifact to the persistence layer for later review or resume

### Strategy and content production
- Selects a single approved idea from the generated batch
- Builds a content strategy with objective, message, tone, and structure
- Creates a master content draft that acts as the canonical story backbone
- Performs grounding review to ensure claims are supported by research

### Platform adaptation
- Customizes content for:
  - YouTube: titles, descriptions, scripts
  - Instagram: hooks, carousel structure, reels script, captions
  - X: single post or thread generation
- Runs platform-level grounding checks to revise weak outputs

### Quality and creative gates
- Validates platform content for compliance with format and messaging constraints
- Stops pipeline execution when a gate fails
- Generates creative briefs and storyboards for visual execution
- Optionally renders images through an enabled image provider

### Operational workflow
- Maintains run state and artifact history in SQLite
- Supports resume-from-failure flows for partially completed runs
- Provides both CLI and Streamlit interfaces

## Architecture

The project follows a layered architecture:

- Agents: LLM-backed specialists for research, ideas, strategy, grounding, quality, platform content, creative planning, and publishing
- Workflows: LangGraph-based orchestration of multi-step tasks
- Pipeline service: orchestrates the full end-to-end generation lifecycle
- Persistence: stores runs, artifacts, statuses, and generated content
- Services: LLM, search, image generation, and publishing integrations
- UI: Streamlit pages for content creation, dashboard, review, and publishing

## Project Structure

```text
.
├── main.py                     # CLI entry point
├── streamlit_app.py            # Streamlit dashboard entry point
├── pyproject.toml              # Package metadata and dependencies
├── requirements.txt            # Python dependency list
├── README.md                  # Project documentation
├── data/                      # SQLite DB, input, output, and generated assets
├── docs/                      # Project docs
├── logs/                      # Log output
├── prompts/                   # Prompt templates or prompt artifacts
├── src/
│   └── social_media_agent/
│       ├── agents/            # LLM-specialized agents
│       ├── config/            # Settings and environment config
│       ├── core/              # Logging and shared utilities
│       ├── models/            # Pydantic models for workflow states and outputs
│       ├── persistence/       # DB models, repository, run tracking
│       ├── services/          # LLM, search, image, quality, publishing
│       ├── ui/                # Streamlit pages and dependencies
│       ├── workflows/         # LangGraph workflow construction
│       └── __init__.py
├── tests/                     # Automated tests for workflows and pipeline behavior
└── .env.example               # not present in repo; configure your own environment file
```

## Runtime Flow

The main pipeline is implemented in `ContentPipelineService` and usually proceeds as follows:

1. Generate research and content ideas
2. Human approval of the chosen idea
3. Build strategy and master content
4. Run grounding review
5. Generate platform content for recommended channels
6. Run platform grounding and revision loops
7. Validate final content with the quality gate
8. Generate creative asset briefs
9. Optionally create images
10. Mark the run ready for human review or publishing

This is not a simple single-call LLM app; it is a multi-stage agent workflow with persisted intermediate outputs and retry logic.

## Configuration

The app reads settings from environment variables and `.env` via `pydantic-settings`.

Key settings include:

- `llm_provider`: default is `ollama`
- `ollama_base_url`: default `http://localhost:11434`
- `ollama_model`: default `qwen3:4b-instruct`
- `database_url`: default SQLite path under `data/database/social_media_agent.db`
- `search_provider`: default `ddgs`
- `image_generation_enabled`: default `False`
- `publishing_mode`: default `dry_run`
- `max_grounding_retries`, `max_platform_grounding_retries`, `max_quality_retries`

Example `.env` values:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:4b-instruct
SEARCH_PROVIDER=ddgs
IMAGE_GENERATION_ENABLED=false
PUBLISHING_MODE=dry_run
DATABASE_URL=sqlite:///./data/database/social_media_agent.db
```

## Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

or, for an editable local install:

```bash
pip install -e .
```

### 3. Ensure model/provider services are available

This project defaults to Ollama-based LLM access. Confirm Ollama is running locally and the model is available before running generation jobs.

If image generation is enabled, configure the provider-specific environment settings such as `OPENAI_API_KEY` and related model settings.

## Running the CLI

The main entry point is `main.py`.

### Create a new run

```bash
python main.py --topic "AI in software testing" --audience "QA engineers"
```

### Resume an existing run

```bash
python main.py --run-id "<run-id>"
```

The CLI creates a run, persists intermediate artifacts, and prints the final output report after the workflow completes or resumes.

## Running the Streamlit UI

```bash
streamlit run streamlit_app.py
```

The app provides:

- Dashboard
- Create Content page
- Content Review page
- Publishing page

## Testing

The repository includes workflow and persistence tests under `tests/`.

Run the suite with:

```bash
pytest
```

## Dependencies

The project depends on the following main libraries:

- `langgraph` for orchestration
- `pydantic` and `pydantic-settings` for schemas and settings
- `sqlalchemy` for persistence
- `streamlit` for UI
- `ddgs` for web search
- `requests` for LLM network calls
- `loguru` for logging

## Notes on Behavior

- The project assumes an LLM provider is available at runtime.
- Search and generation perform actual network work, so the app is best run with a proper internet connection and valid provider credentials.
- The default publishing mode is `dry_run`, which prevents live post publication unless explicitly configured.
- Failures are intentionally tracked per run so a user can resume from a failed grounding or quality gate.

## Typical Usage Scenario

1. Select a content topic and audience.
2. Let the system research and generate several ideas.
3. Pick the best idea from the list.
4. Review generated strategy and master content.
5. Let the system turn the content into platform-specific packages.
6. Inspect validation reports and regenerate if needed.
7. Continue to creative planning and optional image generation.
8. Publish or move the approved output into a downstream workflow.

## License

This project does not currently declare an explicit license in the repository metadata. Check the repository root for any additional license files before commercial use.

## Summary

The codebase is best understood as an agentic content production workflow with explicit phases, structured models, database-backed persistence, and multiple execution modes. It is designed for research-backed, reusable, platform-aware social content generation rather than a single-shot prompt wrapper.
