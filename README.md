# PolicyPilot

A governed regulatory/policy Q&A copilot — the first of three portfolio projects
demonstrating agentic AI patterns on Databricks + Azure (Q&A, AI reviewer, generation).
PolicyPilot answers questions about SEC 10-K filings and cites the filing each answer references. Citation syntax and coverage are checked; semantic support
requires separate evaluation.

## Review status (October 17, 2026)

This is a research prototype, not a production compliance decision system.
The original archive contains historical deployment notes from its author; those
notes do not establish that your own Azure resources exist or have been tested.
See [the engineering review](docs/ENGINEERING_REVIEW.md) for fixes and remaining work.

The agent checks citation coverage and reference bounds. It cannot prove that a
cited passage supports a claim. Human review and semantic groundedness evaluation
remain necessary. There is no application-level tenant isolation or user authorization.
Databricks runs with the application's service principal; per-user data access is
not implemented by this code.

## Architecture

| Layer | Local | Databricks/Azure |
|---|---|---|
| Vector store | `retrieval/local_chroma.py` (Chroma + sentence-transformers) | `retrieval/databricks_vector_search.py` — Vector Search over `policypilot_dev.filings.chunks` (implemented, endpoint/index not created yet) |
| LLM | `agent/llm.py` `GroqLLMClient`, key from `.env` — guardrail-free by design (dev sandbox) | `DatabricksGatewayLLMClient` calling the `<catalog>.filings.gpt-oss` Unity Gateway model service (`resources/ai_gateway.yml`), which routes to Groq through a provider service holding the key, with guardrails — no raw Groq key in the App's env anymore, see [docs/UPGRADE_PLAN.md](docs/UPGRADE_PLAN.md) |
| Structured lookup | `ingestion/manifest.py` (local JSON) | UC Function over a Delta table (not built yet) |
| UI | `streamlit run` locally | Databricks App (`resources/apps.yml` + `app.yaml`, deploys the whole repo since the app imports the full `policypilot` package) |
| Ingestion | `python -m policypilot.ingestion.pipeline` | `notebooks/seed_chunks_table.py` (manual, self-contained) |

Switch backends via `PP_ENV` (`local` or `databricks`). The agent itself
(`agent/graph.py`, a LangGraph plan → retrieve → answer → verify loop) never changes —
it only talks to the `VectorStore` and `LLMClient` protocols in `retrieval/base.py` and
`agent/llm.py`.

### Deferred: not Mosaic AI yet

Databricks' "Mosaic AI" branding covers Agent Framework (log an agent to Unity Catalog
via MLflow, deploy behind Model Serving), Agent Evaluation, and Agent Bricks. This
project includes Agent Evaluation (manual workflow dispatch, see below) and Unity AI Gateway (governance for
the Groq call) but not the rest — the agent itself still runs as plain LangGraph, not
logged to UC or served behind Model Serving. Full Foundation Model migration (swapping
Groq for a Databricks-native model) was deliberately reversed — see
[docs/UPGRADE_PLAN.md](docs/UPGRADE_PLAN.md) item 3 — since a Unity Gateway model service in
front of Groq provides the same guardrails without a provider migration.

The agent is deliberately not a bare RAG chain: `verify_node` is a hard citation gate —
an answer with no `[n]` citation back to retrieved context is replaced with a refusal
before it reaches the user.

## Local setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11+.

```bash
uv sync --locked --extra dev
cp .env.example .env
# edit .env: set GROQ_API_KEY and SEC_EDGAR_USER_AGENT with your real contact email
```

### 1. Ingest filings

Pulls the latest 10-K for ~20 large-cap tickers (`DEFAULT_TICKERS` in `config.py`) from
SEC EDGAR (public, no auth), chunks them, embeds them locally, and stores them in
`data/chroma/`.

```bash
uv run python -m policypilot.ingestion.pipeline
```

### 2. Run the chat UI

```bash
uv run streamlit run src/policypilot/app/streamlit_app.py
```

### 3. Run the eval harness

Runs the golden question set (~47 questions across all ingested tickers, plus one
deliberately off-corpus question to check the refusal gate) through the agent via
Databricks Agent Evaluation (`mlflow.genai.evaluate`, `mlflow[databricks]>=3.1`). The
hosted judges (safety, relevance, retrieval groundedness) need Databricks workspace auth;
the citation-presence check runs locally either way.

```bash
uv sync --locked --extra dev --extra eval
uv run python -m policypilot.eval.agent_eval
```

### Tests

```bash
uv run pytest
uv run ruff check .
```

## Configure your own deployment

1. Configure your own workspace through `DATABRICKS_HOST` and unified authentication.
2. Supply `BUNDLE_VAR_admin_user` and `BUNDLE_VAR_groq_api_key` securely at deploy time.
3. Create your catalog, seed the chunks table, and provision the Vector Search index.
4. Set `PP_UC_CATALOG`, `PP_UC_SCHEMA`, `PP_VECTOR_SEARCH_ENDPOINT`, and
   `PP_VECTOR_SEARCH_INDEX` in the App environment to match those resources.
5. Validate the bundle before deployment. Staging and production remain templates;
   manual CD currently permits only dev.
6. Validate access grants, gateway policies, citations, and refusal behavior in your
   own workspace before exposing the app to users.

Set the `DATABRICKS_ADMIN_USER` GitHub environment variable for CD and the
`SEC_EDGAR_USER_AGENT` variable (including your real contact email) for manual evaluation.
Cloud evaluation runs only through manual CI workflow dispatch and requires secrets.
Normal push/PR checks use deterministic offline retrieval tests (real Chroma storage,
synthetic embeddings); these do not measure embedding relevance or model quality.

## Repo layout

```
src/policypilot/
├── config.py               # env-driven settings, local vs. databricks backend selection
├── ingestion/               # SEC EDGAR fetch -> chunk -> embed -> store
├── retrieval/                # VectorStore protocol + local/Databricks implementations
├── agent/                    # LLM client protocol, tools, LangGraph agent
├── eval/                     # golden dataset + Databricks Agent Evaluation harness
└── app/                       # Streamlit chat UI (becomes the Databricks App)
notebooks/seed_chunks_table.py # Self-contained: fetch+chunk+embed+write into UC, run in-workspace
scripts/setup_unity_catalog.py # UC provisioning script (dev catalog was created by hand instead)
resources/, databricks.yml     # Databricks Asset Bundle (deploy config)
app.yaml, requirements.txt     # Databricks App runtime config (repo root, since app.yml deploys the whole repo)
.github/workflows/              # CI (active) + CD (manual-dispatch, until GitHub OIDC is wired up)
```
