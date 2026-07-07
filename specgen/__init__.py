"""specgen — AI-assisted test generation for the API testing framework.

Pipeline: OpenAPI 3.x spec in -> Claude-generated PyTest files out.

    spec_parser  Load an OpenAPI spec and slice it into per-endpoint chunks
    prompts      Versioned prompt templates (the design artifact)
    generator    One Claude API call per endpoint, with a syntax-validation gate
    writer       Quarantine generated files under tests/generated/
    report       Generation summary: coverage, token usage, failures

Generated code is never trusted as-is: it lands in tests/generated/ and only
moves to tests/curated/ after a documented human critique pass (see
evaluation/EVALUATION.md).

Deliberately NOT built (scope guardrails):
    - no agent loops or self-healing tests — one generation pass, one retry
      on invalid syntax, nothing else
    - no UI or dashboard — CLI only (python -m specgen --spec ...)
    - no CI integration in v1
    - no fine-tuning, RAG, or embeddings
"""

__version__ = "0.1.0"
