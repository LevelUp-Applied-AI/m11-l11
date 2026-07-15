"""Observability layer for the M10 backend.

This module is where you (the learner) declare the three Prometheus metric
families and implement the three ASGI middleware classes that the autograder
exercises through the FastAPI app.

What lives here, and why:

  - Three metric families. A counter for request volume by (path, status), a
    histogram for request latency by path, and a gauge for in-flight requests.
    Together they answer "how much traffic, how slow, how concurrent."

  - Three middlewares. A request-id layer that attaches a per-request
    correlation id to the response and to the logging context. A
    structured-logging layer that emits one JSON line per response. A metrics
    layer that increments the counter, observes the latency histogram, and
    brackets the request with the in-flight gauge.

  Ordering matters: request-id is outermost (so it wraps the logging line),
  logging is middle, metrics is innermost (closest to the route).

Where to put what:

  - Declarations at MODULE SCOPE. If you declare a Counter / Histogram / Gauge
    inside a function or inside a middleware __call__, you will hit
    `Duplicated timeseries in CollectorRegistry` on the second request --
    every request re-runs the function. Module scope means the registry sees
    the declaration once at import time.

  - Label cardinality matters. The Lab's `requests_total` Counter uses
    exactly two labels: {path, status}. Do NOT add user-id, query-text,
    full-URL, or any other unbounded label.

Methodology pointers:

  - Reading sections 6-10 cover middleware, metric types, label cardinality.
  - See Common Pitfalls #1-#4 in the lab guide.
"""

import time
import uuid
import json
import logging
from contextvars import ContextVar
# TODO: import Counter, Histogram, Gauge from prometheus_client.
from prometheus_client import Counter, Histogram, Gauge

# TODO: declare the three metric families at module scope.
#
#   requests_total           — Counter, labels (path, status)
#   request_latency_seconds  — Histogram, label (path); use the default
#                              Prometheus latency buckets.
#   inflight_requests        — Gauge, no labels.
#
# Do not over-label — see the cardinality discussion in the M11 reading.
requests_total = Counter(
    "requests_total",
    "Total number of HTTP requests processed",
    ["path", "status"]
)

request_latency_seconds = Histogram(
    "request_latency_seconds",
    "HTTP request latency in seconds",
    ["path"]
)

inflight_requests = Gauge(
    "inflight_requests",
    "Number of concurrent in-flight HTTP requests"
)

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

logger = logging.getLogger("m11.api")


# TODO: implement RequestIdMiddleware (ASGI middleware class).
#
#   - __init__(self, app): store app.
#   - __call__(self, scope, receive, send): generate a request id, store it
#     somewhere the logging layer can read (a ContextVar is the standard
#     pattern), and arrange for the outbound response to carry an
#     `X-Request-ID` header.
#
#   The autograder asserts the response header is present and at least 8
#   characters long.
class RequestIdMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        req_id = uuid.uuid4().hex
        request_id_var.set(req_id)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", req_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


# TODO: implement StructuredLoggingMiddleware (ASGI middleware class).
#
#   - On response, emit one JSON line containing the keys:
#       request_id, path, status, latency_ms
#     plus any other keys you find useful. The autograder asserts the four
#     keys above are present and parseable as JSON.
class StructuredLoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        status_code = [200]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code[0] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            
            log_payload = {
                "request_id": request_id_var.get(),
                "path": scope.get("path", ""),
                "status": status_code[0],
                "latency_ms": round(elapsed_ms, 2)
            }
            logger.info(json.dumps(log_payload))


# TODO: implement MetricsMiddleware (ASGI middleware class).
#
#   - On request: increment inflight_requests.
#   - Around the route handler: time the request.
#   - On response: increment requests_total with the (path, status) label
#     pair, observe the latency histogram, decrement inflight_requests.
#
#   Do not include high-cardinality labels (no user id, no query string).
class MetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        inflight_requests.inc()
        start_time = time.perf_counter()
        path = scope.get("path", "")
        status_code = [200]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code[0] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - start_time
            
            requests_total.labels(path=path, status=str(status_code[0])).inc()
            request_latency_seconds.labels(path=path).observe(elapsed)
            inflight_requests.dec()