import json
import os
from typing import Any, Dict, Optional

import allure
import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from api_testing_framework.exceptions import APIError


class APIClient:
    """
    Generic HTTP client that handles requests with optional token refresh hook.
    Subclasses should override `_refresh_token_if_needed` to implement auth flows.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 10.0,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        # Store base URL and optional token
        self.base_url = base_url.rstrip("/")
        self._token = token
        self._token_expires_at: float = 0.0

        # Prepare headers
        headers: Dict[str, str] = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"

        # Instantiate HTTPX client
        client_args: Dict[str, Any] = {
            "base_url": self.base_url,
            "headers": headers,
            "timeout": timeout,
        }

        if transport is not None:
            client_args["transport"] = transport

        self._client = httpx.Client(**client_args)
        self._last_request: Optional[httpx.Request] = None
        self._last_response: Optional[httpx.Response] = None

    def _refresh_token_if_needed(self) -> None:
        """
        No-op by default. Subclasses override to implement token refresh
        """
        return

    def _handle_response(self, response: httpx.Response) -> dict:
        data = response.json()
        if not response.is_success:
            raise APIError(response.status_code, data.get("error", response.text), data)
        return data

    def _record_request(self, request: httpx.Request) -> None:
        """Store the outgoing Request object for later attachment."""
        self._last_request = request

    def _sanitize_payload(self, raw_text: str) -> tuple[str, Any]:
        """
        Truncate and redact JSON paloads based on env settings
        """
        max_chars = int(os.getenv("MAX_PAYLOAD_CHARS", "5120"))
        redact_keys = set(
            filter(None, os.getenv("REDACT_FIELDS", "access_token,password").split(","))
        )

        # Truncate
        text = raw_text
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n<truncated>"

        # Attempt JSON parse and redact
        try:
            parsed = json.loads(text)

            def _red(o):
                if isinstance(o, dict):
                    return {
                        k: ("***REDACTED***" if k in redact_keys else _red(v))
                        for k, v in o.items()
                    }
                if isinstance(o, list):
                    return [_red(i) for i in o]
                return o

            sanitized = json.dumps(_red(parsed), indent=2)
            return sanitized, allure.attachment_type.JSON
        except Exception:
            return text, allure.attachment_type.TEXT

    def _attach_last_exchange_to_allure(self) -> None:
        """
        Attach the most recent httpx.Request and httpx.Response
        (stored in self._last_request / self._last_response) into Allure
        """
        if not (self._last_request and self._last_response):
            return

        # Attach HTTP request
        request: httpx.Request = self._last_request
        allure.attach(
            f"{request.method} {request.url}",
            name="HTTP Request",
            attachment_type=allure.attachment_type.TEXT,
        )

        # Attach request headers
        headers = "\n".join(f"{k}: {v}" for k, v in request.headers.items())
        allure.attach(
            headers, name="Request Headers", attachment_type=allure.attachment_type.TEXT
        )

        # Attach request body
        if self._last_request.content:
            try:
                raw_body = self._last_request.content.decode("utf-8", errors="ignore")
            except Exception:
                raw_body = "<binary content>"
            body_text, atype = self._sanitize_payload(raw_body)
            allure.attach(body_text, name="Request Body", attachment_type=atype)

        # Attach response status
        response: httpx.Response = self._last_response
        allure.attach(
            f"{response.status_code} {response.reason_phrase}",
            name="HTTP Response Status",
            attachment_type=allure.attachment_type.TEXT,
        )

        # Attach response headers
        response_headers = "\n".join(f"{k}: {v}" for k, v in response.headers.items())
        allure.attach(
            response_headers,
            name="Response Headers",
            attachment_type=allure.attachment_type.TEXT,
        )

        # Attach response body
        raw_response = response.text or ""
        response_text, atype = self._sanitize_payload(raw_response)
        allure.attach(response_text, name="Response Body", attachment_type=atype)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(APIError),
    )
    def get(
        self, path: str, params: Dict[str, Any] = None, *, attach: bool = False
    ) -> dict:
        """
        GET request; if attach=True, record & attach the request/response in Allure
        """
        self._refresh_token_if_needed()

        # Build request
        request = self._client.build_request("GET", path, params=params)
        if attach:
            self._record_request(request)

        # Send and record response
        response = self._client.send(request)
        if attach:
            self._last_response = response

        # Handle status; if it errors, attach before raising
        try:
            data = self._handle_response(response)
        except APIError:
            if attach:
                self._attach_last_exchange_to_allure()
            raise

        # On success, attach if requested
        if attach:
            self._attach_last_exchange_to_allure()
        return data

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(APIError),
    )
    def post(
        self, path: str, json: Dict[str, Any] = None, *, attach: bool = False
    ) -> dict:
        """
        POST request; if attach=True, record & attach the request/response in Allure
        """
        self._refresh_token_if_needed()

        # Build request
        request = self._client.build_request("POST", path, json=json)
        if attach:
            self._record_request(request)

        # Send and record response
        response = self._client.send(request)
        if attach:
            self._last_response = response

        # Handle status; if errors, attach before raising
        try:
            data = self._handle_response(response)
        except APIError:
            if attach:
                self._attach_last_exchange_to_allure()
            raise

        # On success, attach if requested
        if attach:
            self._attach_last_exchange_to_allure()
        return data

    def put(
        self, path: str, json: Dict[str, Any] = None, *, attach: bool = False
    ) -> dict:
        """
        PUT request; if attach=True, record & attach the request/response in Allure.
        """
        self._refresh_token_if_needed()

        # Build the request
        request = self._client.build_request("PUT", path, json=json)
        if attach:
            self._record_request(request)

        # Send and record response
        response = self._client.send(request)
        if attach:
            self._last_response = response

        # Handle status; if it errors, attach before raising
        try:
            data = self._handle_response(response)
        except APIError:
            if attach:
                self._attach_last_exchange_to_allure()
            raise

        # On success, attach if requested
        if attach:
            self._attach_last_exchange_to_allure()
        return data

    def delete(self, path: str, *, attach: bool = False) -> dict:
        """
        DELETE request; if attach=True, record & attach the request/response in Allure.
        """

        self._refresh_token_if_needed()

        # Build request
        request = self._client.build_request("DELETE", path)
        if attach:
            self._record_request(request)

        # Send and record response
        response = self._client.send(request)
        if attach:
            self._last_response = response

        # Handle status; if it errors, attach before raising
        try:
            data = self._handle_response(response)
        except APIError:
            if attach:
                self._attach_last_exchange_to_allure()
            raise

        # On success, attach if requested
        if attach:
            self._attach_last_exchange_to_allure()
        return data
