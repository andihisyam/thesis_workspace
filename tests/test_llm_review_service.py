import pytest

from app.services import llm_review_service


class _DummyResponse:
    def __init__(self, content: str):
        self.choices = [type("Choice", (), {"message": type("Message", (), {"content": content})()})()]


class _DummyClient:
    def __init__(self, contents: list[str] | str):
        if isinstance(contents, str):
            self._contents = [contents]
        else:
            self._contents = list(contents)
        self.calls: list[dict] = []
        self.chat = type("Chat", (), {"completions": type("Completions", (), {"create": self.create})()})()

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content = self._contents.pop(0) if self._contents else "{}"
        return _DummyResponse(content)


def test_build_llm_suggestions_accepts_alternative_keys(monkeypatch):
    payload = '{"summary":"ok","issues":[{"title":"Masalah kutipan","detail":"Rapikan format sitasi","priority":"high","evidence":"[1][2]","reason":"Agar konsisten"}]}'
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    monkeypatch.setattr(llm_review_service, "OpenAI", lambda **_kwargs: _DummyClient(payload))

    suggestions, summary = llm_review_service.build_llm_suggestions(["Paragraf contoh."], "cek sitasi", "Bab I")

    assert summary == "ok"
    assert suggestions == [{
        "issue": "Masalah kutipan",
        "suggestion": "Rapikan format sitasi",
        "severity": "high",
        "excerpt": "[1][2]",
        "replacement": "",
        "reason": "Agar konsisten",
    }]


def test_build_llm_suggestions_retries_when_replacement_is_english(monkeypatch):
    first_payload = '{"summary":"awal","suggestions":[{"issue":"Kalimat informal","suggestion":"Gunakan bahasa lebih formal","severity":"medium","excerpt":"kalimat asli","replacement":"This sentence should be more formal.","reason":"Lebih akademik"}]}'
    second_payload = '{"summary":"ulang","suggestions":[{"issue":"Kalimat informal","suggestion":"Gunakan bahasa lebih formal","severity":"medium","excerpt":"kalimat asli","replacement":"Kalimat ini sebaiknya dibuat lebih formal.","reason":"Agar sesuai gaya akademik"}]}'
    client = _DummyClient([first_payload, second_payload])
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    monkeypatch.setattr(llm_review_service, "OpenAI", lambda **_kwargs: client)

    suggestions, summary = llm_review_service.build_llm_suggestions(["Paragraf contoh."], "cek gaya bahasa", "Bab I")

    assert summary == "ulang"
    assert suggestions[0]["replacement"] == "Kalimat ini sebaiknya dibuat lebih formal."
    assert len(client.calls) == 2


def test_build_llm_suggestions_falls_back_when_suggestions_missing(monkeypatch):
    payload = '{"summary":"cukup baik"}'
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    monkeypatch.setattr(llm_review_service, "OpenAI", lambda **_kwargs: _DummyClient(payload))

    suggestions, summary = llm_review_service.build_llm_suggestions(["ini paragraf informal banget dan terlalu panjang etc."], "cek gaya bahasa", "Bab I")

    assert suggestions
    assert "fallback lokal" in summary.lower()
