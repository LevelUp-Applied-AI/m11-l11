"""YOUR tests for the observability layer.

Per the lab guide, write at least 3 substantive tests, each with at least
1 assertion. The autograder enforces only the structure (3+ test functions,
each with an `assert` and a non-stub body); the specific behaviors you
choose to verify are up to you.

You name the tests, you decide what to assert, you choose the test
strategy (TestClient + header inspection? caplog + log parsing?
/metrics scrape + counter delta?). The placeholders below show one
possible split (one test per middleware), but you are free to pick any
three behaviors that exercise meaningful properties of your
instrumentation -- e.g. test that the request-id flows across two
sequential requests with distinct ids, test that the metrics counter
reflects a 500 response status correctly, test that the structured log
line carries the X-Request-ID matching the response header.

The autograder does not import your test function names; rename them
freely.
"""

import json
import logging
import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.observability import requests_total

@pytest.fixture
def client():
    return TestClient(app)


def test_one(client):
    # TODO: write a meaningful test of your observability layer here.
    response = client.get("/healthz")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) >= 8


def test_two(client):
    # TODO: write a meaningful test of your observability layer here.
    try:
        initial_value = requests_total.labels(path="/healthz", status="200")._value.get()
    except Exception:
        initial_value = 0

    response = client.get("/healthz")
    assert response.status_code == 200

    final_value = requests_total.labels(path="/healthz", status="200")._value.get()
    assert final_value == initial_value + 1


def test_three(client, caplog):
    # TODO: write a meaningful test of your observability layer here.
    with caplog.at_level(logging.INFO, logger="m11.api"):
        response = client.get("/healthz")
        assert response.status_code == 200
        
        request_id_from_header = response.headers.get("X-Request-ID")
        assert request_id_from_header is not None

        found_matching_log = False
        for record in caplog.records:
            try:
                log_data = json.loads(record.message)
                if log_data.get("request_id") == request_id_from_header:
                    assert log_data["path"] == "/healthz"
                    assert log_data["status"] == 200
                    assert "latency_ms" in log_data
                    found_matching_log = True
                    break
            except json.JSONDecodeError:
                continue

        assert found_matching_log, "Could not find structured JSON log line matching the request_id"