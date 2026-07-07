"""Versioned prompt templates for test generation.

The prompts ARE a design artifact: they encode this framework's quality bar
so the model is onboarded into OUR conventions instead of freestyling.
Bump PROMPT_VERSION on any wording change — the version is stamped into every
generated file header and the generation report, so a batch of output is
always traceable to the exact prompt that produced it.

Design notes (kept next to the rules they explain):

* "Assert status code AND response schema, never status code alone" exists
  because LLMs default to lazy `assert status == 200` tests. The quality bar
  is encoded in the prompt, then verified again in the human critique pass.
* Negative tests are demanded explicitly (missing field, wrong type, 401,
  404) because the model won't volunteer them.
* "Output ONLY valid Python" still fails sometimes, so the generator strips
  markdown fences defensively and gates every file through ast.parse() with
  a single retry. We don't trust the output *format*, let alone the logic.
* Framework-specific contract: our APIClient (httpx wrapper) RAISES
  api_testing_framework.exceptions.APIError on any non-2xx response instead
  of returning it. A generated negative test that asserts on a returned
  status code can never pass against this client — so the prompt spells out
  the pytest.raises(APIError) pattern.
"""

import json

from specgen.spec_parser import EndpointSpec

PROMPT_VERSION = "1.0.0"

SYSTEM_PROMPT = """\
You are generating PyTest test cases for an existing Python REST API testing framework.

Framework facts you MUST respect:
- Tests use the provided `api_client` fixture (an APIClient wrapping httpx.Client, \
supplied by conftest — never construct a client yourself).
- api_client exposes: .get(path, params=None), .post(path, json=None), \
.put(path, json=None), .delete(path). Each returns the parsed JSON response body \
(a dict) on 2xx status codes.
- On ANY non-2xx response the client raises api_testing_framework.exceptions.APIError, \
which has .status_code (int) and .response (dict) attributes. Negative tests MUST use \
`with pytest.raises(APIError) as exc_info:` and assert on `exc_info.value.status_code`. \
Asserting on a returned status code is impossible with this client.

Conventions you MUST follow:
- One test file per endpoint. Import pytest and APIError at the top.
- Every endpoint gets: happy path, missing required field, invalid data type, \
auth failure (401), and not-found (404) — each where applicable to the endpoint.
- Assert status code AND response schema (presence and types of the fields the \
spec guarantees), never a status code alone.
- No hardcoded URLs, tokens, or IDs — use fixtures and conftest values. When a \
test needs an ID or payload, define it via a fixture or module-level constant \
clearly marked as test data.
- Include a docstring on every test stating what it validates and why.
- Mark every test with @pytest.mark.integration (these hit a live API).
- Only test what the spec defines. Do not invent endpoints, parameters, or \
response fields that are not in the provided spec excerpt.

Output ONLY valid Python code. No markdown fences, no commentary.
"""

ENDPOINT_PROMPT_TEMPLATE = """\
Generate PyTest tests for this endpoint.

Endpoint: {method} {path}
Summary: {summary}
Parameters: {params_json}
Request body schema: {request_schema}
Response schemas: {responses_json}
Auth: {security_requirements}
"""

# Sent once, after a syntax failure. One retry only (scope guardrail):
# a model that can't produce parseable Python twice gets recorded as a
# failure in the report, not coaxed through an agent loop.
RETRY_PROMPT_TEMPLATE = """\
Your previous output was not valid Python. ast.parse() failed with:

{syntax_error}

Regenerate the complete test file for {method} {path}. \
Output ONLY valid Python code. No markdown fences, no commentary.
"""


def render_endpoint_prompt(endpoint: EndpointSpec) -> str:
    """Fill the per-endpoint template from a parsed spec slice."""
    return ENDPOINT_PROMPT_TEMPLATE.format(
        method=endpoint.method,
        path=endpoint.path,
        summary=endpoint.summary or "(none)",
        params_json=json.dumps(endpoint.parameters, indent=2, sort_keys=True),
        request_schema=json.dumps(endpoint.request_schema, indent=2, sort_keys=True),
        responses_json=json.dumps(endpoint.responses, indent=2, sort_keys=True),
        security_requirements=json.dumps(endpoint.security, sort_keys=True),
    )


def render_retry_prompt(endpoint: EndpointSpec, syntax_error: str) -> str:
    return RETRY_PROMPT_TEMPLATE.format(
        syntax_error=syntax_error,
        method=endpoint.method,
        path=endpoint.path,
    )
