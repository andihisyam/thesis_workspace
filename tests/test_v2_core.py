import io
import zipfile
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend_v2.database import Base
from backend_v2.main import membership
from backend_v2.models import DocumentPage, DocumentUnit, Project, ReferenceRecord, SourceDocument, User
from backend_v2.reference_service import import_references, map_citations
from backend_v2.security import hash_password, verify_password
from backend_v2.storage import LocalStorageAdapter
from backend_v2.structure_builder import apply_toc_structure, parse_toc_outline
from backend_v2.workspace_service import create_blank_workspace, import_zip, safe_relative_path


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_password_hash_roundtrip() -> None:
    encoded = hash_password("rahasia-kuat")

    assert verify_password("rahasia-kuat", encoded)
    assert not verify_password("salah-password", encoded)


@pytest.mark.parametrize("value", ["../secret.tex", "/etc/passwd", "folder/../../secret"])
def test_workspace_rejects_unsafe_paths(value: str) -> None:
    with pytest.raises(ValueError, match="Path workspace tidak valid"):
        safe_relative_path(value)


def test_blank_workspace_contains_compilable_entry_files(tmp_path: Path) -> None:
    storage = LocalStorageAdapter(tmp_path)
    create_blank_workspace(storage, "projects/one/current")

    assert storage.resolve("projects/one/current/main.tex").exists()
    assert storage.resolve("projects/one/current/references.bib").exists()


def test_zip_import_blocks_path_traversal(tmp_path: Path) -> None:
    storage = LocalStorageAdapter(tmp_path)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../outside.tex", "malicious")

    with pytest.raises(ValueError):
        import_zip(storage, "projects/one/current", buffer.getvalue())

    assert not (tmp_path / "outside.tex").exists()


def test_reference_import_and_citation_mapping(db: Session) -> None:
    project_id = "project-one"
    bib = """@article{smith2023,
  author = {Smith, John},
  title = {Diabetes Research},
  year = {2023},
  journal = {Health Journal}
}
"""
    imported = import_references(db, project_id, bib, "bib")
    unit = DocumentUnit(
        project_id=project_id,
        document_id="document-one",
        level="CHAPTER",
        number="1",
        title="Pendahuluan",
        content="Penelitian sebelumnya menunjukkan perkembangan penting (Smith, 2023).",
        start_page=2,
        end_page=2,
    )
    db.add(unit)
    db.commit()

    citations = map_citations(db, project_id)

    assert imported[0].citation_key == "smith2023"
    assert len(citations) == 1
    assert citations[0].status == "VERIFIED"
    assert citations[0].reference_id == imported[0].id


def test_text_reference_gets_deterministic_key(db: Session) -> None:
    records = import_references(
        db,
        "project-two",
        "Smith, John. (2024). Machine Learning untuk Prediksi Diabetes.",
        "paste",
    )

    assert len(records) == 1
    assert records[0].citation_key.startswith("smith2024")
    assert db.get(ReferenceRecord, records[0].id) is not None


def test_admin_can_access_any_project_without_membership(db: Session) -> None:
    admin = User(email="admin@example.com", display_name="Admin", password_hash="x", is_admin=True)
    regular = User(email="user@example.com", display_name="User", password_hash="x")
    project = Project(name="Project User", description="", created_by="external-user")
    db.add_all([admin, regular, project])
    db.commit()

    assert membership(db, project.id, admin, write=True) == "ADMIN"
    with pytest.raises(HTTPException) as exc:
        membership(db, project.id, regular)
    assert exc.value.status_code == 404



def test_toc_outline_builds_chapter_subchapter_and_subsubchapter(db: Session) -> None:
    document = SourceDocument(project_id="project-structure", filename="skripsi.pdf", storage_key="x")
    db.add(document)
    db.flush()
    db.add_all([
        DocumentPage(document_id=document.id, page_number=1, text="BAB I PENDAHULUAN\nLatar belakang penelitian"),
        DocumentPage(document_id=document.id, page_number=2, text="1.1 Latar Belakang\nIsi latar belakang"),
        DocumentPage(document_id=document.id, page_number=3, text="1.1.1 Konteks Masalah\nIsi konteks masalah"),
    ])
    db.commit()

    outline = parse_toc_outline("""BAB I PENDAHULUAN
1.1 Latar Belakang
1.1.1 Konteks Masalah
""")
    units = apply_toc_structure(db, document, """BAB I PENDAHULUAN
1.1 Latar Belakang
1.1.1 Konteks Masalah
""")

    assert [item.level for item in outline] == ["CHAPTER", "SUBCHAPTER", "SUBSUBCHAPTER"]
    assert [unit.level for unit in units] == ["CHAPTER", "SUBCHAPTER", "SUBSUBCHAPTER"]
    assert units[1].parent_id == units[0].id
    assert units[2].parent_id == units[1].id
    assert units[2].start_page == 3
