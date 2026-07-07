"""Generation report: endpoints covered, token spend, failures.

Written next to the generated tests (same quarantine directory) as both
markdown (human review) and JSON (anything downstream). The report is the
paper trail for the critique pass: which model, which prompt version, what
it cost, and what failed before a human ever reads the test code.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from specgen.generator import GenerationResult
from specgen.prompts import PROMPT_VERSION


@dataclass
class GenerationReport:
    spec_title: str
    spec_version: str
    spec_source: str
    model: str
    prompt_version: str = PROMPT_VERSION
    results: List[GenerationResult] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    )

    @property
    def succeeded(self) -> List[GenerationResult]:
        return [r for r in self.results if r.valid]

    @property
    def failed(self) -> List[GenerationResult]:
        return [r for r in self.results if not r.valid]

    @property
    def total_input_tokens(self) -> int:
        return sum(r.input_tokens for r in self.results)

    @property
    def total_output_tokens(self) -> int:
        return sum(r.output_tokens for r in self.results)

    def to_dict(self) -> dict:
        return {
            "spec": {
                "title": self.spec_title,
                "version": self.spec_version,
                "source": self.spec_source,
            },
            "model": self.model,
            "prompt_version": self.prompt_version,
            "generated_at": self.generated_at,
            "totals": {
                "endpoints": len(self.results),
                "succeeded": len(self.succeeded),
                "failed": len(self.failed),
                "retried": sum(1 for r in self.results if r.retried),
                "input_tokens": self.total_input_tokens,
                "output_tokens": self.total_output_tokens,
            },
            "results": [
                {
                    "endpoint": r.endpoint.label,
                    "valid": r.valid,
                    "retried": r.retried,
                    "error": r.error,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "duration_s": r.duration_s,
                }
                for r in self.results
            ],
        }

    def to_markdown(self) -> str:
        lines = [
            "# specgen generation report",
            "",
            f"- **Spec:** {self.spec_title} v{self.spec_version} (`{self.spec_source}`)",
            f"- **Model:** {self.model}",
            f"- **Prompt version:** {self.prompt_version}",
            f"- **Generated at:** {self.generated_at}",
            f"- **Endpoints:** {len(self.results)} "
            f"({len(self.succeeded)} generated, {len(self.failed)} failed, "
            f"{sum(1 for r in self.results if r.retried)} needed a syntax retry)",
            f"- **Tokens:** {self.total_input_tokens} in / {self.total_output_tokens} out",
            "",
            "| Endpoint | Status | Retried | Tokens (in/out) | Time (s) | Error |",
            "|---|---|---|---|---|---|",
        ]
        for r in self.results:
            status = "ok" if r.valid else "FAILED"
            lines.append(
                f"| `{r.endpoint.label}` | {status} | {'yes' if r.retried else 'no'} "
                f"| {r.input_tokens}/{r.output_tokens} | {r.duration_s} "
                f"| {r.error or ''} |"
            )
        lines += [
            "",
            "_Everything above is unreviewed machine output. The critique pass in_",
            "_`evaluation/EVALUATION.md` decides what gets promoted to `tests/curated/`._",
            "",
        ]
        return "\n".join(lines)

    def write(self, out_dir: Path) -> Path:
        """Write generation_report.md + .json into the quarantine directory."""
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "generation_report.json").write_text(
            json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        md_path = out_dir / "generation_report.md"
        md_path.write_text(self.to_markdown(), encoding="utf-8")
        return md_path
