from typing import Any, Dict, Optional

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

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(APIError),
    )
    def get(self, path: str, params: Dict[str, Any] = None) -> dict:
        """GET with retries on APIError"""
        self._refresh_token_if_needed()
        resp = self._client.get(path, params=params)
        return self._handle_response(resp)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(APIError),
    )
    def post(self, path: str, json: Dict[str, Any] = None) -> dict:
        """POST with retries on APIError"""
        self._refresh_token_if_needed()
        resp = self._client.post(path, json=json)
        return self._handle_response(resp)

    def put(self, path: str, json: Dict[str, Any] = None) -> dict:
        self._refresh_token_if_needed()
        resp = self._client.put(path, json=json)
        return self._handle_response(resp)

    def delete(self, path: str) -> dict:
        self._refresh_token_if_needed()
        resp = self._client.delete(path)
        return self._handle_response(resp)
