import pytest

from app.services import llm_review_service


class _DummyResponse:
    def __init__(self, content: str):
        self.choices = [type("Choice", (), {"message": type("Message", (), {"content": content})()})()]


class _DummyClient:
    def __init__(self, content: str):
        self._content = content
        self.chat = type("Chat", (), {"completions": type("Completions", (), {"create": self.create})()})()

    def create(self, **_kwargs):
        return _DummyResponse(self._content)


def test_build_llm_suggestions_accepts_alternative_keys(monkeypatch):
    payload = '{"summary":"ok","issues":[{"title":"Masalah kutipan","detail":"Rapikan format sitasi","priority":"high","evidence":"[1][2]"}]}'
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    monkeypatch.setattr(llm_review_service, "OpenAI", lambda **_kwargs: _DummyClient(payload))

    suggestions, summary = llm_review_service.build_llm_suggestions(["Paragraf contoh."], "cek sitasi", "Bab I")

    assert summary == "ok"
    assert suggestions == [{
        "issue": "Masalah kutipan",
        "suggestion": "Rapikan format sitasi",
        "severity": "high",
        "excerpt": "[1][2]",
    }]


def test_build_llm_suggestions_falls_back_when_suggestions_missing(monkeypatch):
    payload = '{"summary":"cukup baik"}'
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    monkeypatch.setattr(llm_review_service, "OpenAI", lambda **_kwargs: _DummyClient(payload))

    suggestions, summary = llm_review_service.build_llm_suggestions(["ini paragraf informal banget dan terlalu panjang etc."], "cek gaya bahasa", "Bab I")

    assert suggestions
    assert "fallback lokal" in summary.lower()
