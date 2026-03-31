"""Tests for the HTTP retry logic in gismap.utils.requests."""

import pytest
import requests as req

from gismap.utils.requests import get, session


class FakeResponse:
    def __init__(self, status_code=200, text="ok", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
        self.encoding = None


def test_get_success(monkeypatch):
    """Normal 200 response is returned."""
    monkeypatch.setattr(session, "get", lambda *a, **kw: FakeResponse(text="hello"))
    assert get("http://example.com") == "hello"


def test_get_encoding(monkeypatch):
    """When encoding is specified, it is set on the response."""
    resp = FakeResponse(text="café")

    def fake_get(*a, **kw):
        return resp

    monkeypatch.setattr(session, "get", fake_get)
    get("http://example.com", encoding="utf-8")
    assert resp.encoding == "utf-8"


def test_get_retry_429_with_retry_after(monkeypatch):
    """429 with Retry-After header: retries after the specified delay."""
    calls = []
    responses = [
        FakeResponse(status_code=429, headers={"Retry-After": "1"}),
        FakeResponse(text="recovered"),
    ]

    def fake_get(*a, **kw):
        calls.append(1)
        return responses.pop(0)

    monkeypatch.setattr(session, "get", fake_get)
    monkeypatch.setattr("gismap.utils.requests.sleep", lambda t: None)
    assert get("http://example.com") == "recovered"
    assert len(calls) == 2


def test_get_retry_429_without_retry_after(monkeypatch):
    """429 without Retry-After header: falls back to 60s."""
    sleep_values = []
    responses = [
        FakeResponse(status_code=429, headers={}),
        FakeResponse(text="ok"),
    ]

    monkeypatch.setattr(session, "get", lambda *a, **kw: responses.pop(0))
    monkeypatch.setattr("gismap.utils.requests.sleep", lambda t: sleep_values.append(t))
    get("http://example.com")
    assert sleep_values == [60]


def test_get_retry_connection_error_then_success(monkeypatch):
    """ConnectionError on first attempt, success on second."""
    attempt = [0]

    def fake_get(*a, **kw):
        attempt[0] += 1
        if attempt[0] == 1:
            raise req.exceptions.ConnectionError("fail")
        return FakeResponse(text="recovered")

    monkeypatch.setattr(session, "get", fake_get)
    monkeypatch.setattr("gismap.utils.requests.sleep", lambda t: None)
    assert get("http://example.com") == "recovered"
    assert attempt[0] == 2


def test_get_connection_error_exhaustion(monkeypatch):
    """All attempts fail with ConnectionError -> raises."""
    monkeypatch.setattr(session, "get", lambda *a, **kw: (_ for _ in ()).throw(req.exceptions.ConnectionError("fail")))
    monkeypatch.setattr("gismap.utils.requests.sleep", lambda t: None)
    with pytest.raises(req.exceptions.ConnectionError):
        get("http://example.com", n_trials=3)
