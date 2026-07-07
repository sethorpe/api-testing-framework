# tests/generated/ — quarantine

LLM output lands here, untrusted. `*.py` files and generation reports in this
directory are **gitignored** until they have been through the critique pass.

Nothing in this directory runs in CI or counts as coverage. To trust a test:

1. Run it and read every line.
2. Classify findings against the taxonomy in `evaluation/EVALUATION.md`.
3. Promote a corrected copy to `tests/curated/` (the header comment stays,
   so the provenance — model, prompt version — travels with it).

The two-directory structure is the quality gate: generation is cheap, the
engineering is in the evaluation.
