# PolicyPilot engineering review

Reviewed October 17, 2026 from the supplied archive (upstream archive commit
4ca031c0fe7f6031a6c1c88aea53f4bfe1c6f205).

## Assessment

A useful research prototype with a clear separation between the agent, retrieval,
ingestion, and UI. It is not yet ready for production compliance decisions.
The workflow is a fixed LangGraph plan → retrieve → answer → verify graph; the
planner chooses a search query and company, but there is no iterative tool loop.
The metadata lookup is recorded in state but is not separately routed into answers.

## Findings and changes

| Priority | Finding | Improvement |
|---|---|---|
| High | Any citation, including [999], passed verification | Validate reference bounds and citation coverage per sentence/line; reject incomplete answers |
| High | Evaluation wrapper did not accept ticker and failed on scoped retrieval | Preserve ticker when forwarding search to the underlying store |
| High | Deployment defaulted to another author's workspace/admin | Remove active personal defaults, expose resource names through environment settings |
| High | A typo in PP_ENV silently selected cloud mode | Reject unknown environments |
| High | Invalid chunk overlap could make the loop never terminate | Validate chunk size and overlap, including the standalone notebook |
| Medium | Manifest said ingested even if indexing failed | Record only after successful indexing; atomically replace manifest JSON |
| Medium | Cloud ingestion fetched data before hitting unsupported upsert | Fail before downloads and direct users to the Delta notebook |
| Medium | Notebook appended duplicate chunks on rerun | Merge into the existing Delta table by chunk_id |
| Medium | Ordinary PR CI required cloud secrets and external model calls | Run cloud evaluation only by manual workflow dispatch; use locked dependency resolution |
| Medium | Retrieval tests downloaded an embedding model | Test real Chroma persistence/filtering with injected deterministic embeddings |
| Medium | SEC client lacked retry policy and accepted missing contact | Add bounded GET retries and contact email validation |
| Medium | UI claimed all configured companies were ingested | Show recorded local manifest entries and distinguish managed cloud corpus |
| Medium | UI exposed backend exceptions and lacked history reset | Show generic error messages and add Clear conversation |
| Low | Data path fixed inside installed source tree | Support PP_DATA_DIR |
| Low | Only .env was ignored | Ignore environment variants while preserving .env.example |

## Verification

- 32 tests passed locally on Python 3.12.
- Ruff static checks and Python compilation of src/scripts passed.
- CD reads DATABRICKS_ADMIN_USER from GitHub environment variables; manual evaluation
  reads SEC_EDGAR_USER_AGENT from variables instead of using a fake contact.
- Tests cover the real Chroma storage backend with synthetic embeddings, the agent
  with fake LLM responses, failed index writes, environment validation, chunking,
  and SEC contact/retry configuration.
- The original lockfile is preserved. Local validation used its LangGraph 1.2.11,
  Chroma 1.5.9, pytest 9.1.1, and Ruff 0.16.5 versions; this was not a full locked
  installation of every optional/cloud dependency.
- No live SEC ingestion, Groq call, Streamlit browser session, hosted MLflow judge,
  Databricks bundle validation, or Azure deployment was performed. Those require
  environment-specific configuration and credentials. Notebook merge was reviewed
  statically and requires verification in Databricks.

## Remaining work before production

1. Verify semantic support: a citation checker cannot establish truth. Even with
   sentence coverage, a model can cite an unrelated passage. Add adversarial tests,
   groundedness evaluation, and human review for consequential answers.
2. Define user authorization and data access boundaries. The cloud app uses its own
   service principal; user-delegated authorization and tenant isolation are absent.
3. Define corpus freshness. Reingestion adds new accession IDs without removing old
   filings; queries can retrieve multiple years. Expose filing dates and add explicit
   fiscal-year/accession selection before promising latest-filing answers.
4. Add concurrency-safe ingestion. Atomic manifest writes prevent truncated JSON,
   but concurrent writers can lose updates; use a transactional store or single writer.
5. Verify model quality separately. Offline test embeddings deliberately do not test
   sentence-transformer relevance. Establish live retrieval and refusal baselines.
6. Make hosted evaluation a release gate with thresholds; currently metrics are
   printed, not enforced. Keep paid evaluations separate from ordinary PR checks.
7. Validate and pin cloud CLI/actions and gateway resource compatibility in your own
   workspace. Staging/prod bundle entries remain unconfigured templates.
8. Bound LLM latency/output costs, validate retrieval scores and index response
   schemas, add operational logs/metrics without leaking filing questions or secrets.
9. Replace the setup script's first-warehouse selection and unchecked asynchronous
   DDL responses with an explicit warehouse and checked statement results.
10. Establish upstream provenance/license before redistributing as an open-source
    product. The supplied archive contains no LICENSE; no license was invented here.

## Run locally

```bash
uv sync --locked --extra dev
cp .env.example .env
# Set GROQ_API_KEY and SEC_EDGAR_USER_AGENT to your real contact.
uv run python -m policypilot.ingestion.pipeline
uv run streamlit run src/policypilot/app/streamlit_app.py
```

Cloud evaluation and deployment remain manual. Configure your own Azure/Groq
credentials and resource grants; do not reuse historical author-specific examples.
