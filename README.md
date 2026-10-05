# Incident Investigation AI

An evidence-first incident triage API built with Python and FastAPI. Submit a sanitized incident, retrieve relevant runbook passages, and receive cited hypotheses and investigation checks. Every response distinguishes retrieval evidence from an established root cause.

**Portfolio v0.1:** runnable locally, synthetic data, no credentials required in the default mode. This project was prepared with AI coding assistance. It is a learning and demonstration project, with no claim of production deployment, business impact, or independent authorship. See the [review walkthrough](docs/review-guide.md) to understand and demonstrate the implementation.

## What is implemented

| Capability | Working implementation | Boundary |
| --- | --- | --- |
| API integration | Typed FastAPI REST endpoints; async HTTPX OpenAI Responses adapter; HTTP demo client | OpenAI integration tested with mocked HTTP responses; live paid calls not verified |
| Async execution | Async endpoints and provider I/O, shared HTTP client, bounded investigation concurrency, thread-offloaded retrieval | Single process; no durable jobs or distributed orchestration |
| Error handling | Request limits, validation, deadlines, capped retries, sanitized error envelopes | No circuit breaker or global rate limiter |
| Embeddings and retrieval | Real local sparse TF-IDF vectors and cosine similarity over Markdown chunks | Lexical embeddings, not neural/semantic embeddings |
| Prompt/context handling | Fixed system instructions, JSON evidence envelope, bounded source context, strict response schema, citation allowlist | Citation existence is checked; factual entailment is not automatically verified |
| Small RAG pipeline | Retrieval → bounded context → provider synthesis → citation validation | Mock mode uses deterministic templates; OpenAI mode performs LLM generation |
| Automated verification | Pytest API, retrieval, concurrency, and failure tests; Ruff; GitHub Actions | These are correctness tests, not advanced model evaluation |

ReAct, MCP, multi-agent coordination, A2A, and durable execution are **roadmap items**, not implemented features.

## Quick start

Requires Python 3.11–3.13. Python 3.12 is the locally tested version. Installation needs internet access; once installed, mock mode needs no network access or paid API credentials. No model weights need downloading.

### Windows PowerShell

Open a terminal inside the extracted `incident-investigation-ai` folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

If Windows cannot find Python, install Python 3.12 and reopen the terminal, or use `py -3.12` for the first command. The virtual environment commands avoid PowerShell activation-policy issues. Do not overwrite an existing `.env` when upgrading.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
cp .env.example .env
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

Open [interactive API documentation](http://127.0.0.1:8000/docs). The `/health` endpoint reports the selected provider and indexed chunk count; it does not test OpenAI credentials or connectivity. The startup process validates and indexes the runbooks before accepting requests.

The lock files record exact dependency versions used for verification, without artifact hashes. `pyproject.toml` describes compatible ranges. To experiment with newer compatible dependencies, use `python -m pip install -e ".[dev]"` instead and rerun tests. This is not a supply-chain attestation.

## Run the demo

With the server running, open a second terminal in the same folder. On Windows:

```powershell
.\.venv\Scripts\python.exe -m app.demo
.\.venv\Scripts\python.exe -m app.demo --scenario aem-cache
.\.venv\Scripts\python.exe -m app.demo --scenario unknown
```

On macOS/Linux, activate the environment and use `python -m app.demo` with the same options. The first scenario retrieves database pool runbooks; the AEM scenario retrieves Dispatcher guidance; the unknown scenario returns `insufficient_evidence` with no generated analysis.

### API examples

PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
$body = Get-Content app/data/incidents/database-pool.json -Raw
$result = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/investigations -ContentType 'application/json' -Body $body
$result | ConvertTo-Json -Depth 10
```

curl (on Windows use `curl.exe`):

```bash
curl -s http://127.0.0.1:8000/health
curl -s -H "Content-Type: application/json" --data-binary @app/data/incidents/database-pool.json http://127.0.0.1:8000/v1/investigations
curl -s -H "Content-Type: application/json" -d '{"query":"OOMKilled memory pressure","top_k":2}' http://127.0.0.1:8000/v1/search
```

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Local readiness and provider mode |
| GET | `/v1/runbooks` | Runbook titles and chunk counts |
| POST | `/v1/search` | Inspect retrieval without generation |
| POST | `/v1/investigations` | Retrieve evidence and produce triage guidance |
| GET | `/docs` | Swagger UI and editable request examples |

An investigation request contains `incident` (title, description, optional service/severity/signals) and optional `top_k` (1–5). The response contains `status`, `provider`, `generation_mode`, `analysis`, `evidence`, `warnings`, and `request_id`. Each hypothesis/check references exact chunk IDs present in `evidence`. Similarity scores are **not confidence probabilities**. No diagnostic commands are executed.

Error responses share this structure:

```json
{"error":{"code":"provider_timeout","message":"The model provider timed out.","request_id":"generated-per-request"}}
```

Relevant statuses: 408 for a slow request body; 413 for an oversized body; 422 for invalid input; 502 for rejected/malformed upstream responses or invalid citations; 503 for provider rate limits; 504 for timeouts; 500 for unexpected failures. Unknown evidence is a successful 200 response with `status="insufficient_evidence"`, not an infrastructure error.

## Optional OpenAI mode

Edit the untracked `.env`:

```dotenv
PROVIDER=openai
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4o-mini
```

Restart the server. Use a model your API project can access that supports the Responses API and strict JSON Schema output. The example model is configurable; availability is not assumed. No API key is supplied with the project, and no live paid request was made during verification.

The adapter uses asynchronous HTTPX requests to the fixed HTTPS endpoint `https://api.openai.com/v1/responses`, passes structured output configuration, and sets `store=false`. See [OpenAI's structured output documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses). Input incident text and selected runbooks are sent externally in this mode. `store=false` is not a guarantee of zero provider retention. Use synthetic or appropriately sanitized data. Provider errors are surfaced explicitly; the app does not silently substitute mock answers.

## Configuration

Environment variables override `.env`; configuration is read when the app factory runs.

| Variable | Default | Purpose |
| --- | --- | --- |
| `PROVIDER` | `mock` | `mock` or `openai` |
| `OPENAI_API_KEY` | unset | Required only for OpenAI mode; masked in settings representation |
| `OPENAI_MODEL` | `gpt-4o-mini` | Responses-compatible model name |
| `RUNBOOK_DIR` | packaged `app/data/runbooks` | Optional custom Markdown corpus; restart to re-index |
| `MIN_SIMILARITY` | `0.12` | Cosine cutoff; illustrative, not calibrated |
| `MAX_CONTEXT_CHARS` | `12000` | Serialized runbook-source budget; excludes incident and system text |
| `REQUEST_TIMEOUT_SECONDS` | `30` | Investigation deadline, including semaphore queueing |
| `PROVIDER_TIMEOUT_SECONDS` | `10` | HTTPX per-operation timeout per attempt |
| `PROVIDER_MAX_ATTEMPTS` | `2` | Total attempts, including the first; maximum 3 |
| `MAX_CONCURRENT_INVESTIGATIONS` | `8` | Active investigations per worker |
| `MAX_REQUEST_BYTES` | `65536` | Body byte limit, including streamed bodies |
| `LOG_LEVEL` | `INFO` | Application log verbosity |

App logs are JSON with event, request ID, status, and elapsed time. They exclude incident bodies, API keys, and raw provider errors. Uvicorn access logging is disabled in the documented commands to avoid logging user-controlled URLs. This does not add automatic redaction to incident data supplied by users.

## Tests and checks

Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing --cov-fail-under=85
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m build
```

On macOS/Linux use `python` in the activated environment. Tests use HTTP mocks and synthetic data; they do not contact the paid provider. GitHub Actions runs the checks on Python 3.11, 3.12, and 3.13 when pushed. A workflow file is not proof of a successful remote run; inspect the Actions tab after upload. See [verification results](docs/validation.md) for what was actually run locally.

## Docker

Requires a running Docker engine:

```bash
docker build -t incident-investigation-ai .
docker run --rm -p 127.0.0.1:8000:8000 --env PROVIDER=mock incident-investigation-ai
```

The image runs as a non-root user and has a health check. For OpenAI mode, use `--env-file .env` and protect that file. Docker was not executed locally because the Docker engine was unavailable. The host-based setup and tests are the verified path.

## Design and limitations

- Small services separate retrieval, prompting, generation, orchestration, and API concerns. See [architecture](docs/architecture.md).
- TF-IDF avoids model downloads and makes ranking inspectable, but misses synonyms and semantic relationships. It is appropriate for a small lexical baseline, not a claim of state-of-the-art retrieval.
- Mock generation reuses evidence in a fixed template. It tests plumbing and produces repeatable demonstrations; it is not model reasoning.
- The optional LLM can make unsupported claims even with valid citations. Prompt boundaries and schema validation reduce some mistakes but do not solve prompt injection or hallucination.
- All six runbooks and three incidents are synthetic educational examples, including the AEM scenario. They are not copied from an employer or validated operational procedures.
- The API has no authentication, persistence, multi-tenancy, distributed limits, or production monitoring. Run it on loopback for demonstrations. Add these controls before exposing it to other users.
- Limits bound individual bodies, corpus size, active investigations, and context. Waiting requests are not bounded globally; use gateway admission controls before a public deployment.
- No output is an approved remediation plan or confirmed root cause. Operators remain responsible for investigation and change approval.

## Roadmap

1. Add a curated relevance dataset, retrieval metrics, citation entailment checks, and human review labels.
2. Implement optional neural embeddings and compare them with the TF-IDF baseline before replacing it.
3. Add authenticated read-only monitoring integrations with explicit data handling rules.
4. Introduce a bounded ReAct/tool loop only when tools, stop conditions, and approval boundaries exist.
5. Explore MCP for tool access and durable job state for longer investigations.
6. Consider multi-agent/A2A coordination only if a measured use case justifies the added complexity.

## Publish to the personal repository

See [exact Git commands](docs/publish.md) for `frombinlearn-png/incident-investigation-ai`. Review the source and run the demo before presenting it. The verification record distinguishes local checks from remote CI.
