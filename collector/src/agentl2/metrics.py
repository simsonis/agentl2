from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Optional

from .logging import get_logger

logger = get_logger("agentl2.metrics")


class _JobMetrics:
    __slots__ = ("collected_total", "skipped_duplicates", "failed_total", "last_run_started", "last_run_finished")

    def __init__(self) -> None:
        self.collected_total: int = 0
        self.skipped_duplicates: int = 0
        self.failed_total: int = 0
        self.last_run_started: Optional[float] = None
        self.last_run_finished: Optional[float] = None


class MetricsServer:
    """Lightweight metrics server exposing text-format counters on /metrics."""

    def __init__(self, port: int) -> None:
        self._port = port
        self._metrics: Dict[str, _JobMetrics] = {}
        self._lock = threading.Lock()
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        handler = self._build_handler()

        self._httpd = ThreadingHTTPServer(("0.0.0.0", self._port), handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="metrics-server", daemon=True)
        self._thread.start()
        self._started = True
        logger.info("metrics server started", port=self._port)

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread:
            self._thread.join(timeout=2)
        self._started = False

    def record_run_start(self, job: str) -> None:
        with self._lock:
            metrics = self._metrics.setdefault(job, _JobMetrics())
            metrics.last_run_started = time.time()

    def record_run_end(self, job: str, collected: int, duplicates: int, failures: int) -> None:
        with self._lock:
            metrics = self._metrics.setdefault(job, _JobMetrics())
            metrics.collected_total += collected
            metrics.skipped_duplicates += duplicates
            metrics.failed_total += failures
            metrics.last_run_finished = time.time()

    def _build_handler(self):
        outer = self

        class _MetricsHandler(BaseHTTPRequestHandler):
            def do_GET(self):  # type: ignore[override]
                if self.path != "/metrics":
                    self.send_error(404, "Not Found")
                    return
                payload = outer._render_metrics().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_args, **_kwargs):  # type: ignore[override]
                return

        return _MetricsHandler

    def _render_metrics(self) -> str:
        lines = ["# agentl2 collection metrics"]
        with self._lock:
            for job, metrics in self._metrics.items():
                labels = f'{{job="{job}"}}'
                lines.append(f"collected_total{labels} {metrics.collected_total}")
                lines.append(f"skipped_duplicates{labels} {metrics.skipped_duplicates}")
                lines.append(f"failed_total{labels} {metrics.failed_total}")
                if metrics.last_run_started is not None:
                    lines.append(f"last_run_started{labels} {metrics.last_run_started:.3f}")
                if metrics.last_run_finished is not None:
                    lines.append(f"last_run_finished{labels} {metrics.last_run_finished:.3f}")
        return "\n".join(lines) + "\n"
