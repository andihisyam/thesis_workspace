from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.services.thesis_repository import ThesisRepository
from backend.app.api.routers import documents as documents_router
from backend.app.main import app


def test_healthcheck_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_document_endpoints_use_repository_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    thesis_root = tmp_path / "thesis"
    thesis_root.mkdir()
    (thesis_root / "chapter2.tex").write_text(
        "\\chapter{Teori}\n\\section{Diabetes}\nIsi diabetes.",
        encoding="utf-8",
    )
    monkeypatch.setattr(documents_router, "repository", ThesisRepository(thesis_root))

    with TestClient(app) as client:
        documents = client.get("/api/documents")
        structure = client.get("/api/documents/chapter2.tex/structure")
        content = client.get(
            "/api/documents/chapter2.tex/content",
            params={"scope": "section", "target_id": "section:1"},
        )

    assert documents.status_code == 200
    assert documents.json() == {"items": ["chapter2.tex"]}
    assert [item["label"] for item in structure.json()["items"]] == [
        "Bab 2 - Teori",
        "2.1 Diabetes",
    ]
    assert content.status_code == 200
    assert content.json()["source_text"] == "Isi diabetes."
