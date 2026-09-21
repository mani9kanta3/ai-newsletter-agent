import json

import pytest

from backend import ai
from backend.schemas import Review


class Response:
    def __init__(self, status, text=''):
        self.status_code = status
        self.text = text

    def json(self):
        return {'candidates': [{'content': {'parts': [{'text': self.text}]}}]}


def test_incomplete_json_retries_then_validates(monkeypatch):
    calls = []
    valid = {'passed': True, 'summary': 'The source claims are supported.', 'issues': []}

    def post(*args, **kwargs):
        calls.append(kwargs)
        return Response(200, 'incomplete' if len(calls) == 1 else json.dumps(valid))

    monkeypatch.setattr(ai, 'API_KEY', 'test-key')
    monkeypatch.setattr(ai.requests, 'post', post)
    assert ai.ask_gemini('Review this draft', {}, Review) == valid
    assert len(calls) == 2


@pytest.mark.parametrize('status, expected', [
    (429, 'usage limit'),
    (403, 'rejected the API key'),
    (404, 'not available to your account'),
    (503, 'temporarily unable')
])
def test_provider_errors_are_clear_and_do_not_expose_keys(monkeypatch, status, expected):
    monkeypatch.setattr(ai, 'API_KEY', 'private-test-key')
    monkeypatch.setattr(ai.requests, 'post', lambda *args, **kwargs: Response(status))
    monkeypatch.setattr(ai.time, 'sleep', lambda seconds: None)
    with pytest.raises(RuntimeError) as error:
        ai.ask_gemini('Review this draft', {}, Review)
    assert expected in str(error.value)
    assert 'private-test-key' not in str(error.value)


def test_busy_model_backs_off_then_falls_back(monkeypatch):
    valid = {'passed': True, 'summary': 'The source claims are supported.', 'issues': []}
    urls, waits = [], []

    def post(url, **kwargs):
        urls.append(url)
        return Response(200, json.dumps(valid)) if 'fallback-model' in url else Response(503)

    monkeypatch.setattr(ai, 'API_KEY', 'test-key')
    monkeypatch.setattr(ai, 'MODEL', 'main-model')
    monkeypatch.setattr(ai, 'FALLBACK_MODEL', 'fallback-model')
    monkeypatch.setattr(ai.requests, 'post', post)
    monkeypatch.setattr(ai.time, 'sleep', waits.append)
    assert ai.ask_gemini('Review this draft', {}, Review) == valid
    assert sum('main-model' in url for url in urls) == 4
    assert waits == [2, 4, 8]
    assert 'fallback-model' in urls[-1]


def test_quota_error_does_not_retry_or_fall_back(monkeypatch):
    calls = []

    def post(url, **kwargs):
        calls.append(url)
        return Response(429)

    monkeypatch.setattr(ai, 'API_KEY', 'test-key')
    monkeypatch.setattr(ai, 'FALLBACK_MODEL', 'fallback-model')
    monkeypatch.setattr(ai.requests, 'post', post)
    with pytest.raises(RuntimeError, match='usage limit'):
        ai.ask_gemini('Review this draft', {}, Review)
    assert len(calls) == 1
