"""
client.py
---------
Low-level Binance Futures Testnet REST client.

Responsibilities:
  - Manage API key / secret
  - Sign requests (HMAC-SHA256)
  - Send HTTP requests with retry logic (bonus feature)
  - Surface Binance API errors as clean Python exceptions
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # seconds between retries


# ── Custom exceptions ─────────────────────────────────────────────────────────

class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response or error payload."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceNetworkError(Exception):
    """Raised on network-level failures (timeouts, connection errors)."""


# ── Client ────────────────────────────────────────────────────────────────────

class BinanceFuturesClient:
    """
    Thin, authenticated HTTP client for Binance USDT-M Futures Testnet.

    Usage:
        client = BinanceFuturesClient(api_key="...", api_secret="...")
        response = client.post("/fapi/v1/order", params={...})
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("Both api_key and api_secret must be provided.")

        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

        # Persistent connection pool for efficiency
        self._http = httpx.Client(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        logger.info("BinanceFuturesClient initialised — base_url=%s", self._base_url)

    # ── Signing ───────────────────────────────────────────────────────────────

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add timestamp + HMAC-SHA256 signature to *params* (mutates and returns).
        Binance requires the signature to be the *last* query parameter.
        """
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        sign: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute an HTTP request with retry logic.

        Args:
            method: "GET" | "POST" | "DELETE"
            path:   API endpoint path (e.g. "/fapi/v1/order")
            params: Query / body parameters
            sign:   Whether to sign the request

        Returns:
            Parsed JSON response as a dict.

        Raises:
            BinanceAPIError:     On API-level errors.
            BinanceNetworkError: On transport-level errors.
        """
        params = params or {}
        if sign:
            params = self._sign(params)

        last_exc: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(
                    "HTTP %s %s — attempt %d/%d | params=%s",
                    method, path, attempt, MAX_RETRIES,
                    {k: v for k, v in params.items() if k != "signature"},
                )

                if method.upper() == "GET":
                    response = self._http.get(path, params=params)
                elif method.upper() == "POST":
                    # Binance Futures POST: params go in the body as form-encoded
                    response = self._http.post(path, data=params)
                elif method.upper() == "DELETE":
                    response = self._http.delete(path, params=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                logger.info(
                    "HTTP %s %s — status=%d", method, path, response.status_code
                )

                return self._handle_response(response)

            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                wait = RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)]
                logger.warning(
                    "Network error on attempt %d/%d: %s — retrying in %ds",
                    attempt, MAX_RETRIES, exc, wait,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(wait)

        raise BinanceNetworkError(
            f"Request failed after {MAX_RETRIES} attempts: {last_exc}"
        ) from last_exc

    @staticmethod
    def _handle_response(response: httpx.Response) -> Dict[str, Any]:
        """Parse the HTTP response; raise BinanceAPIError for error payloads."""
        try:
            data = response.json()
        except Exception as exc:
            raise BinanceAPIError(-1, f"Non-JSON response: {response.text}") from exc

        # Binance encodes errors with a numeric `code` and `msg` field
        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            code = data.get("code", -1)
            msg = data.get("msg", "Unknown error")
            logger.error("Binance API error — code=%s msg=%s", code, msg)
            raise BinanceAPIError(code, msg)

        logger.debug("Response payload: %s", data)
        return data

    # ── Public convenience methods ────────────────────────────────────────────

    def post(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", path, params)

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("GET", path, params)

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> "BinanceFuturesClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
