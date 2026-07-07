"""CLI entry point: python -m specgen --spec specs/petstore-openapi.yaml

Scope guardrails enforced here:
- hard cap of 8 endpoints per run (enough data for the evaluation taxonomy,
  small enough to review every generated line honestly)
- no watch mode, no CI hooks, no dashboard — parse, generate, write, report
"""

import argparse
import sys
from pathlib import Path

from specgen.generator import DEFAULT_MODEL, TestGenerator
from specgen.report import GenerationReport
from specgen.spec_parser import SpecParseError, parse_spec
from specgen.writer import DEFAULT_OUT_DIR, write_test

MAX_ENDPOINTS_HARD_CAP = 8


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m specgen",
        description="Generate PyTest tests from an OpenAPI 3.x spec via the Claude API.",
    )
    parser.add_argument(
        "--spec", required=True, help="OpenAPI 3.x spec file (JSON or YAML)"
    )
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help="Quarantine directory for generated tests (default: tests/generated)",
    )
    parser.add_argument(
        "--include",
        default=None,
        help="Only endpoints whose path contains this substring (e.g. /pet)",
    )
    parser.add_argument(
        "--max-endpoints",
        type=int,
        default=MAX_ENDPOINTS_HARD_CAP,
        help=f"Endpoints per run, capped at {MAX_ENDPOINTS_HARD_CAP} (scope guardrail)",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"Model ID (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse the spec and list the endpoints that would be generated; no API calls",
    )
    return parser


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)

    try:
        parsed = parse_spec(args.spec, include=args.include)
    except SpecParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    limit = min(args.max_endpoints, MAX_ENDPOINTS_HARD_CAP)
    if args.max_endpoints > MAX_ENDPOINTS_HARD_CAP:
        print(
            f"note: --max-endpoints clamped to {MAX_ENDPOINTS_HARD_CAP} "
            "(review every generated line, or don't generate it)",
            file=sys.stderr,
        )
    selected = parsed.endpoints[:limit]

    print(
        f"{parsed.title} v{parsed.version}: {len(parsed.endpoints)} endpoints parsed, "
        f"{len(selected)} selected"
    )
    for endpoint in selected:
        print(f"  {endpoint.label}")

    if args.dry_run:
        return 0
    if not selected:
        print("error: no endpoints matched", file=sys.stderr)
        return 2

    generator = TestGenerator(model=args.model)
    report = GenerationReport(
        spec_title=parsed.title,
        spec_version=parsed.version,
        spec_source=parsed.source,
        model=args.model,
    )
    out_dir = Path(args.out_dir)

    for endpoint in selected:
        print(f"generating {endpoint.label} ...", flush=True)
        result = generator.generate(endpoint)
        report.results.append(result)
        if result.valid:
            target = write_test(result, out_dir)
            print(f"  -> {target}")
        else:
            print(f"  -> FAILED: {result.error}")

    report_path = report.write(out_dir)
    totals = report.to_dict()["totals"]
    print(
        f"\ndone: {totals['succeeded']}/{totals['endpoints']} endpoints, "
        f"{totals['input_tokens']} in / {totals['output_tokens']} out tokens"
    )
    print(f"report: {report_path}")
    print(
        "next: review every file, classify findings in evaluation/EVALUATION.md, "
        "promote corrected tests to tests/curated/"
    )
    return 0 if not report.failed else 1


if __name__ == "__main__":
    sys.exit(main())
