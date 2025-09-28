from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional
from urllib.parse import urljoin

import requests
from requests import Response
from tenacity import RetryError, Retrying, retry_if_exception_type, stop_after_attempt, wait_random_exponential


class RateLimitError(Exception):
    pass


@dataclass(frozen=True)
class APIResponse:
    url: str
    status_code: int
    headers: Mapping[str, Any]
    json: Any
    text: str


class APIClient:
    def __init__(
        self,
        *,
        base_url: str,
        default_params: Optional[Dict[str, Any]] = None,
        user_agent: str = "agentl2-collector/0.1",
        timeout: float = 15.0,
        rate_limit_rps: float = 3.0,
        max_retries: int = 5,
        backoff_seconds: float = 1.0,
    ) -> None:
        self._base_url = base_url.rstrip("/") + "/"
        self._default_params = default_params or {}
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": user_agent, "Accept": "application/json"})
        self._retry = Retrying(
            stop=stop_after_attempt(max_retries),
            wait=wait_random_exponential(multiplier=backoff_seconds, max=30),
            retry=retry_if_exception_type((RateLimitError, requests.HTTPError, requests.ConnectionError, requests.Timeout)),
            reraise=True,
        )
        self._lock = threading.Lock()
        self._token_capacity = max(rate_limit_rps, 1.0)
        self._tokens = self._token_capacity
        self._fill_rate = rate_limit_rps
        self._last_refill = time.monotonic()

    def close(self) -> None:
        self._session.close()

    def request_json(self, path: str, params: Optional[Mapping[str, Any]] = None) -> APIResponse:
        def _send() -> APIResponse:
            self._acquire_token()
            merged_params = self._merge_params(params)
            response = self._session.get(
                urljoin(self._base_url, path),
                params=merged_params,
                timeout=self._timeout,
            )
            self._verify_response(response)
            payload = self._parse_response(response)
            return APIResponse(
                url=str(response.url),
                status_code=response.status_code,
                headers=dict(response.headers),
                json=payload,
                text=response.text,
            )

        try:
            return self._retry(_send)
        except RetryError as exc:
            raise exc.last_attempt.exception() or exc

    def _merge_params(self, extra: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
        merged = dict(self._default_params)
        if extra:
            for key, value in extra.items():
                if value is not None:
                    merged[key] = value
        return merged

    def _acquire_token(self) -> None:
        if self._fill_rate <= 0:
            return
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._token_capacity, self._tokens + elapsed * self._fill_rate)
            self._last_refill = now
            if self._tokens < 1:
                sleep_for = (1 - self._tokens) / self._fill_rate
                time.sleep(max(sleep_for, 0))
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(self._token_capacity, self._tokens + elapsed * self._fill_rate)
                self._last_refill = now
            self._tokens -= 1

    @staticmethod
    def _verify_response(response: Response) -> None:
        if response.status_code == 429:
            raise RateLimitError("rate limit exceeded")
        if response.status_code >= 500:
            response.raise_for_status()

    @staticmethod
    def _parse_response(response: Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return None
