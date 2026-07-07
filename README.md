# api-testing-framework

A reusable Python API testing framework built on **httpx**, **PyTest**, and
**Allure**: a retrying `APIClient` base with token-refresh hooks, request/
response capture with payload redaction and truncation, and attach-on-failure
reporting.

## specgen — AI-assisted test generation (with a human gate)

`specgen` extends the framework with an LLM test-generation pipeline:

> **Input:** an OpenAPI 3.x spec (JSON/YAML)
> **Process:** one Claude API call per endpoint generates PyTest test cases
> **Output:** runnable test files in a quarantine directory + a generation report
> **Human layer:** a documented critique pass (`evaluation/EVALUATION.md`)
> classifying what the model got right, wrong, and dangerously wrong

Honest framing: this is a personal project exploring what AI-assisted testing
actually buys you. The generation is the easy part. The interesting artifact
is the evaluation gate — generated code is treated like a draft from a fast,
overconfident junior, and nothing is trusted until it survives review.

### Usage

```bash
poetry install --with specgen
export ANTHROPIC_API_KEY=...

# See what would be generated (no API calls)
python -m specgen --spec specs/petstore-openapi.yaml --dry-run

# Generate tests for up to 8 endpoints into tests/generated/
python -m specgen --spec specs/petstore-openapi.yaml --include /pet
```

The target spec (Swagger Petstore, OpenAPI 3.0) is pinned in
`specs/petstore-openapi.yaml` so runs are reproducible.

### How it's wired (deliberate design decisions)

1. **One endpoint per API call.** Chunking keeps context focused, makes
   failures isolatable, and keeps per-call token cost visible in the report.
2. **The prompt is a quality contract.** `specgen/prompts.py` (versioned)
   onboards the model into *this* framework's conventions: the `api_client`
   fixture, `pytest.raises(APIError)` for negative tests (our client raises
   on non-2xx rather than returning), schema assertions — never a bare
   status-code check — and explicit negative coverage the model wouldn't
   volunteer.
3. **Generated code is quarantined.** Output lands in `tests/generated/`
   (gitignored) and only moves to `tests/curated/` after the critique pass.
   The two-directory structure is the shift-left quality gate in miniature.
4. **Reproducible by construction.** Pinned model ID, versioned prompts,
   pinned spec — every generated file's header records all three. (Current
   Claude models reject sampling parameters, so "temperature 0" is no longer
   the determinism lever; provenance is.)
5. **The output format isn't trusted either.** Every response is stripped of
   stray markdown fences and gated through `ast.parse()` — one retry on
   syntax failure, then it's recorded as a failure in the report.

### Deliberately not built

- No agent loops, self-healing tests, or multi-step tool use — one clean
  generation pass with retry-on-invalid-syntax only.
- No UI or dashboard — the CLI is enough.
- No CI integration in v1 (the obvious next step: run curated tests in CI
  and use coverage gaps to drive targeted re-generation).
- No fine-tuning, RAG, or embeddings — deliberately boring architecture;
  the judgment lives in the evaluation.
- Never more than 8 endpoints per run — enough data for the failure-mode
  taxonomy, small enough to review every line honestly.

### Evaluation

`evaluation/EVALUATION.md` holds the six-category failure-mode taxonomy
(correct & valuable → dangerous if trusted → missing entirely). It is filled
in by hand during review; findings, counts, and corrected snippets land there
before any test is promoted.

## Development

```bash
make install   # poetry install
make lint      # black, isort, flake8
make test      # pytest (unit + specgen pipeline tests run offline)
make report    # Allure report
```
