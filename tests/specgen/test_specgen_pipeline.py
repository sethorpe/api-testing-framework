"""Unit tests for the specgen pipeline — no API calls, no network.

Covers the pieces that must be right before spending a single token:
spec parsing/$ref resolution, the ast.parse syntax gate (including the
one-retry guardrail), fence stripping, and the quarantine writer.
"""

import json
from dataclasses import dataclass, field
from typing import List

import pytest

from specgen.generator import (GenerationResult, TestGenerator,
                               strip_markdown_fences, validate_python)
from specgen.spec_parser import EndpointSpec, SpecParseError, parse_spec
from specgen.writer import WriterError, generated_filename, write_test

MINIMAL_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Mini API", "version": "1.2.3"},
    "security": [{"api_key": []}],
    "paths": {
        "/pet/{petId}": {
            "parameters": [
                {
                    "name": "petId",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                },
            ],
            "get": {
                "summary": "Find pet by ID",
                "operationId": "getPetById",
                "responses": {
                    "200": {
                        "description": "ok",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Pet"}
                            }
                        },
                    },
                    "404": {"description": "not found"},
                },
            },
            "delete": {
                "summary": "Delete a pet",
                "responses": {"200": {"description": "ok"}},
                "security": [{"oauth": ["write:pets"]}],
            },
        },
    },
    "components": {
        "schemas": {
            "Pet": {
                "type": "object",
                "required": ["name"],
                "properties": {"name": {"type": "string"}},
            }
        }
    },
}


@pytest.fixture
def spec_file(tmp_path):
    path = tmp_path / "mini.json"
    path.write_text(json.dumps(MINIMAL_SPEC))
    return str(path)


@pytest.mark.unit
class TestSpecParser:
    def test_extracts_endpoints_with_merged_parameters(self, spec_file):
        parsed = parse_spec(spec_file)
        assert parsed.title == "Mini API"
        assert [e.label for e in parsed.endpoints] == [
            "DELETE /pet/{petId}",
            "GET /pet/{petId}",
        ]
        get = next(e for e in parsed.endpoints if e.method == "GET")
        # path-level parameters are merged into every operation
        assert get.parameters[0]["name"] == "petId"

    def test_resolves_refs_into_response_schema(self, spec_file):
        get = next(e for e in parse_spec(spec_file).endpoints if e.method == "GET")
        schema = get.responses["200"]["schema"]
        assert schema["properties"]["name"] == {"type": "string"}

    def test_operation_security_overrides_document_default(self, spec_file):
        endpoints = {e.method: e for e in parse_spec(spec_file).endpoints}
        assert endpoints["GET"].security == [{"api_key": []}]
        assert endpoints["DELETE"].security == [{"oauth": ["write:pets"]}]

    def test_include_filter(self, spec_file):
        assert parse_spec(spec_file, include="/nope").endpoints == []

    def test_rejects_non_openapi3(self, tmp_path):
        bad = tmp_path / "swagger2.json"
        bad.write_text(json.dumps({"swagger": "2.0"}))
        with pytest.raises(SpecParseError):
            parse_spec(str(bad))


@pytest.mark.unit
class TestSyntaxGate:
    def test_strips_markdown_fences(self):
        fenced = "```python\nassert True\n```"
        assert strip_markdown_fences(fenced) == "assert True"

    def test_plain_code_untouched(self):
        assert strip_markdown_fences("x = 1\n") == "x = 1"

    def test_validate_python(self):
        assert validate_python("def f():\n    return 1\n") is None
        assert "line" in validate_python("def f(:\n")


@dataclass
class _FakeBlock:
    text: str
    type: str = "text"


@dataclass
class _FakeUsage:
    input_tokens: int = 100
    output_tokens: int = 50


@dataclass
class _FakeResponse:
    content: List[_FakeBlock]
    usage: _FakeUsage = field(default_factory=_FakeUsage)
    stop_reason: str = "end_turn"


class _FakeClient:
    """Stands in for anthropic.Anthropic; returns scripted responses."""

    def __init__(self, texts):
        self._texts = list(texts)
        self.calls = 0
        self.messages = self

    def create(self, **kwargs):
        self.calls += 1
        return _FakeResponse(content=[_FakeBlock(text=self._texts.pop(0))])


def _endpoint():
    return EndpointSpec(method="GET", path="/pet/{petId}", summary="", operation_id="")


@pytest.mark.unit
class TestGeneratorGate:
    def test_valid_first_attempt(self):
        gen = TestGenerator(client=_FakeClient(["import pytest\n"]))
        result = gen.generate(_endpoint())
        assert result.valid and not result.retried
        assert result.input_tokens == 100

    def test_single_retry_then_success(self):
        gen = TestGenerator(client=_FakeClient(["def broken(:", "x = 1\n"]))
        result = gen.generate(_endpoint())
        assert result.valid and result.retried

    def test_gives_up_after_one_retry(self):
        client = _FakeClient(["def broken(:", "still broken ("])
        result = TestGenerator(client=client).generate(_endpoint())
        assert not result.valid
        assert client.calls == 2  # scope guardrail: exactly one retry
        assert "invalid Python" in result.error


@pytest.mark.unit
class TestWriter:
    def test_filename_convention(self):
        assert generated_filename("GET", "/pet/{petId}") == "test_pet_petid_get.py"
        assert generated_filename("POST", "/store/order") == "test_store_order_post.py"

    def test_writes_header_and_code(self, tmp_path):
        result = GenerationResult(
            endpoint=_endpoint(), code="import pytest\n", valid=True
        )
        target = write_test(result, out_dir=tmp_path)
        content = target.read_text()
        assert content.startswith("# GENERATED by specgen")
        assert "GET /pet/{petId}" in content
        assert content.endswith("import pytest\n")

    def test_refuses_invalid_result(self, tmp_path):
        result = GenerationResult(endpoint=_endpoint(), code=None, valid=False)
        with pytest.raises(WriterError):
            write_test(result, out_dir=tmp_path)
