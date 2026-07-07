"""Claude API calls: one endpoint slice in, one PyTest file out.

Design decisions (deliberate, see README):
- One endpoint per API call. Chunking keeps context focused, makes failures
  isolatable, and keeps per-call token cost visible in the report.
- Syntax gate before anything is written: strip markdown fences defensively,
  then ast.parse(). On failure, exactly ONE retry with the error fed back.
  No agent loops, no self-healing — that's a scope guardrail, not a TODO.
- Reproducibility: the model ID and PROMPT_VERSION are pinned and recorded
  per result. The spec file itself is pinned in specs/. Note: current Claude
  models (Opus 4.7+) reject sampling parameters (temperature/top_p), so
  "temperature 0" is no longer a determinism lever — pinned model + versioned
  prompts + pinned spec are.
"""

import ast
import re
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional

from specgen.prompts import (PROMPT_VERSION, SYSTEM_PROMPT,
                             render_endpoint_prompt, render_retry_prompt)
from specgen.spec_parser import EndpointSpec

DEFAULT_MODEL = "claude-opus-4-8"
MAX_OUTPUT_TOKENS = 8000
MAX_SYNTAX_RETRIES = 1  # scope guardrail: retry-on-invalid-syntax only, once

_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_-]*\n|\n?```\s*$")


@dataclass
class GenerationResult:
    """Outcome of generating tests for one endpoint."""

    endpoint: EndpointSpec
    code: Optional[str] = None
    valid: bool = False
    retried: bool = False
    error: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    duration_s: float = 0.0
    model: str = DEFAULT_MODEL
    prompt_version: str = PROMPT_VERSION


def strip_markdown_fences(text: str) -> str:
    """Remove ``` fences the model was told not to emit but sometimes does."""
    return _FENCE_RE.sub("", text.strip()).strip()


def validate_python(code: str) -> Optional[str]:
    """Return None if code parses, else the SyntaxError message."""
    try:
        ast.parse(code)
        return None
    except SyntaxError as exc:
        return f"{exc.msg} (line {exc.lineno})"


class TestGenerator:
    """Drives one generation pass per endpoint against the Claude API."""

    __test__ = False  # "Test" prefix is domain naming, not a pytest class

    def __init__(self, model: str = DEFAULT_MODEL, client: Any = None):
        self.model = model
        if client is None:
            # Lazy import so the rest of specgen (parser, writer, report)
            # works without the anthropic package installed.
            import anthropic

            client = anthropic.Anthropic()
        self._client = client

    def _call(self, messages: List[dict]) -> Any:
        return self._client.messages.create(
            model=self.model,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

    @staticmethod
    def _extract_text(response: Any) -> str:
        return "".join(block.text for block in response.content if block.type == "text")

    def generate(self, endpoint: EndpointSpec) -> GenerationResult:
        """Generate a test file for one endpoint, gated through ast.parse()."""
        result = GenerationResult(endpoint=endpoint, model=self.model)
        messages = [{"role": "user", "content": render_endpoint_prompt(endpoint)}]
        started = time.monotonic()

        try:
            for attempt in range(1 + MAX_SYNTAX_RETRIES):
                response = self._call(messages)
                result.input_tokens += response.usage.input_tokens
                result.output_tokens += response.usage.output_tokens

                if response.stop_reason == "refusal":
                    result.error = "model declined the request (stop_reason=refusal)"
                    break
                if response.stop_reason == "max_tokens":
                    result.error = f"output truncated at {MAX_OUTPUT_TOKENS} tokens"
                    break

                code = strip_markdown_fences(self._extract_text(response))
                syntax_error = validate_python(code)
                if syntax_error is None:
                    result.code = code
                    result.valid = True
                    break

                result.error = (
                    f"invalid Python after {attempt + 1} attempt(s): {syntax_error}"
                )
                if attempt < MAX_SYNTAX_RETRIES:
                    result.retried = True
                    messages = messages + [
                        {"role": "assistant", "content": self._extract_text(response)},
                        {
                            "role": "user",
                            "content": render_retry_prompt(endpoint, syntax_error),
                        },
                    ]
        except Exception as exc:  # API/network errors become report rows, not crashes
            result.error = f"{type(exc).__name__}: {exc}"

        result.duration_s = round(time.monotonic() - started, 2)
        return result
