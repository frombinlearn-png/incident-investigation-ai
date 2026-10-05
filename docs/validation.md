# Verification record

Verified on **6 October 2026, Asia/Kolkata** (5 October UTC) using Windows and Python **3.12.14**. All results below describe this local build; they do not imply a remote CI run or production deployment.

| Check | Observed result |
| --- | --- |
| Pytest | **73 passed**, no failures |
| Coverage | **95.70%** combined statement/branch coverage; 85% gate passed |
| Ruff lint | Passed for application and tests |
| Ruff formatting | Applied and checked for application and tests |
| Python distribution build | Source distribution and universal Python wheel built successfully |
| Installed wheel | Installed into an isolated environment; runbooks and incident JSON included |
| Live HTTP smoke test | Uvicorn launched from outside the source folder using the installed wheel |
| Health | HTTP 200; mock mode; 18 indexed chunks |
| Database scenario | HTTP 200; completed; database pool passages retrieved with citations |
| AEM scenario | HTTP 200; completed; Dispatcher passages retrieved with citations |
| Unknown scenario | HTTP 200; insufficient evidence; null analysis and empty evidence |
| OpenAI integration | Verified using HTTPX mock transport, including endpoint, Authorization header, schema, response parsing, retries, timeouts, refusal, and invalid output |

The test suite checks input validation, streamed request size rejection, safe error messages, no incident text in application logs, deterministic retrieval, relevant first matches for six scenarios, unknown-query abstention, malformed corpus rejection, context budget accounting, citation membership, concurrent request overlap, concurrency caps, cancellation, and semaphore release after timeout.

The installed Starlette test client emitted one upstream deprecation warning about its HTTPX integration. The tests pass with the exact pinned versions; the warning is not suppressed. This is a future test-client migration consideration, not a live-provider result.

## Commands used

The normal equivalents from the repository root are:

```bash
python -m pytest -q --cov=app --cov-report=term-missing --cov-fail-under=85
python -m ruff check app tests
python -m ruff format --check app tests
python -m build --no-isolation
```

The build used the preinstalled, pinned setuptools backend. This desktop environment's bundled Python required installing into an isolated virtual environment through its parent pip, and Windows sandbox restrictions required permission to use temporary build/test files. Those environment restrictions did not require weakening assertions or skipping tests. Standard Python installations can use the README's normal virtual-environment commands.

## Not verified here

- A live OpenAI request: no paid API key was used. Account/model availability and live schema acceptance need a real integration check when configured.
- Docker build/run: the Docker CLI exists, but its Linux engine was not running.
- GitHub Actions and Python 3.11/3.13: the workflow is included, but only Python 3.12 was executed locally.
- Production load, security accreditation, fault tolerance across workers, semantic retrieval quality, model factuality, or advanced evaluations.

These omissions are deliberate boundaries of the portfolio v1, not completed features.
