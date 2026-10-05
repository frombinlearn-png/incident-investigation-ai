# Ten-minute review walkthrough

This project was prepared with AI assistance. Use the walkthrough to understand the code and identify what you can confidently explain. Do not describe generated code as work you independently designed or deployed.

## Demonstrate the running system

1. Start mock mode using the README. Show `/health`: `provider=mock`, `embedding_method=tfidf`, and an indexed corpus.
2. Open `/docs`, expand `POST /v1/investigations`, and submit `app/data/incidents/database-pool.json`. Explain that it is a synthetic incident.
3. Show the source excerpts, similarity scores, cited hypothesis, and warning that the response is a template. Explain that a matching runbook is not a confirmed cause.
4. Use `POST /v1/search` with `OOMKilled memory pressure` to isolate retrieval from generation.
5. Submit the unknown incident. Explain why the service abstains instead of generating an unsupported analysis.
6. Submit `top_k=6`. Show the sanitized 422 response and its request ID.
7. Run the test suite. Open the provider retry, fabricated-citation, and concurrent-request tests.
8. Trace one request through `main.py`, `investigation_service.py`, `retrieval_service.py`, `prompt_service.py`, and `llm_service.py`.

## Questions to be able to answer

**Are these real embeddings?** They are sparse TF-IDF numeric text representations. They support cosine similarity but are lexical, not learned neural embeddings. Synonyms without word overlap may be missed.

**Where is the LLM?** Only the optional `OpenAIProvider` invokes a model. Default `MockProvider` uses a fixed extractive template and says so in every response. The integration has tests against simulated HTTP responses; a successful live model call has not been claimed.

**Why use async?** Network calls wait without blocking the event loop, and the app reuses an HTTP client. Retrieval is CPU work offloaded to a thread pool. A concurrency test uses a rendezvous to prove two provider calls overlap, and another test verifies the configured active-call limit.

**How is hallucination handled?** Source context is bounded; strict schema validation rejects malformed output; citation checks reject IDs outside the supplied evidence. These do not prove that a cited passage supports every claim. Human review remains necessary.

**What happens during provider failures?** Transient failures have capped retries, all investigations have a deadline, errors are sanitized, and the system does not disguise provider failure as a successful mock response.

**What makes this RAG?** Retrieved passages condition synthesis. Mock mode exercises retrieval-augmented templating; OpenAI mode supplies the same passages to an LLM. There is no multi-step agent loop.

**Why no vector database?** Eighteen sample chunks do not require one. An in-memory baseline is easy to inspect. The decision should be revisited for larger corpora, persistence, filters, and concurrent updates.

**What would you do before production?** Establish corpus ownership, authenticated access, secret/PII handling, gateway limits, observability, model cost limits, provider verification, and relevance/grounding evaluation. The current code is a local portfolio API.

## A useful small change to make yourself

Add a synthetic runbook for a failure you understand. Add a retrieval test proving that an appropriate query ranks it first and a query that should not match it. Restart the server to index it, inspect the evidence, and explain why your wording changes the TF-IDF ranking. This is a concrete way to build ownership beyond running generated code.
