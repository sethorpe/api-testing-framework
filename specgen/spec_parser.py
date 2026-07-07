"""Load an OpenAPI 3.x spec and extract per-endpoint slices for generation.

One EndpointSpec per (path, method) pair. Each slice carries everything the
prompt template needs — parameters, request/response schemas, security — with
local $refs resolved inline so the model never sees a dangling pointer.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

# Guard against pathological or circular $ref chains; real specs stay shallow.
MAX_REF_DEPTH = 30


class SpecParseError(Exception):
    """Raised when the spec cannot be loaded or is not OpenAPI 3.x."""


@dataclass
class EndpointSpec:
    """A single operation, sliced out of the spec for one generation call."""

    method: str  # uppercase, e.g. "GET"
    path: str  # e.g. "/pet/{petId}"
    summary: str
    operation_id: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_schema: Optional[Dict[str, Any]] = None
    responses: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    security: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"{self.method} {self.path}"


@dataclass
class ParsedSpec:
    title: str
    version: str
    source: str
    endpoints: List[EndpointSpec] = field(default_factory=list)


def _load_document(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:
            raise SpecParseError(
                "YAML spec requires PyYAML: pip install pyyaml "
                "(or poetry install --with specgen)"
            ) from exc
        return yaml.safe_load(text)
    return json.loads(text)


def _resolve_refs(node: Any, doc: Dict[str, Any], depth: int = 0) -> Any:
    """Inline local $ref pointers (#/components/...) recursively."""
    if depth > MAX_REF_DEPTH:
        # Circular schema (e.g. self-referencing model): stop expanding and
        # leave a marker so the prompt still shows *something* sensible.
        return {"$circular": True}

    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            target: Any = doc
            for part in ref[2:].split("/"):
                if not isinstance(target, dict) or part not in target:
                    raise SpecParseError(f"Unresolvable $ref: {ref}")
                target = target[part]
            return _resolve_refs(target, doc, depth + 1)
        return {k: _resolve_refs(v, doc, depth + 1) for k, v in node.items()}

    if isinstance(node, list):
        return [_resolve_refs(item, doc, depth + 1) for item in node]

    return node


def _json_body_schema(content: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Pull the application/json schema out of a requestBody/response content map."""
    if not content:
        return None
    media = content.get("application/json") or {}
    return media.get("schema")


def parse_spec(path: str, include: Optional[str] = None) -> ParsedSpec:
    """Parse an OpenAPI 3.x spec file into per-endpoint slices.

    Args:
        path: JSON or YAML spec file.
        include: optional substring filter on the endpoint path
                 (e.g. "/pet" keeps only pet endpoints).
    """
    spec_path = Path(path)
    if not spec_path.is_file():
        raise SpecParseError(f"Spec file not found: {path}")

    doc = _load_document(spec_path)
    if not isinstance(doc, dict) or not str(doc.get("openapi", "")).startswith("3"):
        raise SpecParseError(f"Not an OpenAPI 3.x document: {path}")

    info = doc.get("info", {})
    default_security = doc.get("security", [])
    endpoints: List[EndpointSpec] = []

    for api_path in sorted(doc.get("paths", {})):
        if include and include not in api_path:
            continue
        path_item = _resolve_refs(doc["paths"][api_path], doc)
        shared_params = path_item.get("parameters", [])

        # Sorted for deterministic output ordering across runs.
        for method in sorted(path_item):
            operation = path_item[method]
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue

            responses = {
                status: {
                    "description": resp.get("description", ""),
                    "schema": _json_body_schema(resp.get("content")),
                }
                for status, resp in operation.get("responses", {}).items()
            }

            endpoints.append(
                EndpointSpec(
                    method=method.upper(),
                    path=api_path,
                    summary=operation.get("summary", ""),
                    operation_id=operation.get("operationId", ""),
                    parameters=shared_params + operation.get("parameters", []),
                    request_schema=_json_body_schema(
                        operation.get("requestBody", {}).get("content")
                    ),
                    responses=responses,
                    # Operation-level security overrides the document default.
                    security=operation.get("security", default_security),
                )
            )

    return ParsedSpec(
        title=info.get("title", ""),
        version=info.get("version", ""),
        source=str(spec_path),
        endpoints=endpoints,
    )
