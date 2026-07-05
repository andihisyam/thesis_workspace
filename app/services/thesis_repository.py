import json
from datetime import datetime
from pathlib import Path
import re
from typing import Any

from app.services.latex_revision_sanitizer import sanitize_revision_latex
from app.services.latex_structure_service import parse_latex_structure, resolve_review_unit


class ThesisRepository:
    def __init__(self, thesis_root: Path) -> None:
        self.thesis_root = thesis_root
        self.project_root = thesis_root.parent

    @property
    def revision_drafts_dir(self) -> Path:
        drafts_dir = self.project_root / "data" / "revision_drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        return drafts_dir

    def list_tex_files(self) -> list[str]:
        return sorted(
            path.name
            for path in self.thesis_root.glob("*.tex")
            if path.name not in {"main.tex", "appendices.tex"}
        )

    def read_tex(self, filename: str) -> str:
        file_path = self.thesis_root / filename
        return file_path.read_text(encoding="utf-8")

    def read_binary(self, relative_path: str) -> bytes:
        return (self.project_root / relative_path).read_bytes()

    def save_tex(self, filename: str, content: str) -> None:
        file_path = self.thesis_root / filename
        file_path.write_text(content, encoding="utf-8")

    def save_revision_draft(
        self,
        filename: str,
        selected_label: str,
        content: str,
        metadata: dict[str, Any],
    ) -> Path:
        drafts_dir = self.revision_drafts_dir
        safe_label = re.sub(r"[^A-Za-z0-9._-]+", "_", selected_label).strip("_")
        tex_path = drafts_dir / f"{Path(filename).stem}__{safe_label}.tex"
        json_path = drafts_dir / f"{Path(filename).stem}__{safe_label}.json"

        sanitized_content = sanitize_revision_latex(content)
        sanitized_metadata = dict(metadata)
        sanitized_metadata["selected_file"] = filename
        sanitized_metadata["selected_label"] = selected_label
        sanitized_metadata["revised_text"] = sanitize_revision_latex(
            str(sanitized_metadata.get("revised_text", sanitized_content))
        )
        sanitized_metadata.setdefault("is_active_for_full_document", False)
        sanitized_metadata.setdefault("created_at", datetime.now().isoformat())
        sanitized_metadata["updated_at"] = datetime.now().isoformat()

        tex_path.write_text(sanitized_content, encoding="utf-8")
        json_path.write_text(json.dumps(sanitized_metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return tex_path

    def _sanitize_draft_payload(self, json_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
        tex_path = json_path.with_suffix(".tex")
        sanitized_payload = dict(payload)
        changed = False

        revised_text = sanitized_payload.get("revised_text")
        sanitized_revised_text = sanitize_revision_latex(revised_text) if isinstance(revised_text, str) else ""
        if isinstance(revised_text, str) and sanitized_revised_text != revised_text:
            sanitized_payload["revised_text"] = sanitized_revised_text
            changed = True

        if tex_path.exists():
            tex_content = tex_path.read_text(encoding="utf-8")
            sanitized_tex_content = sanitize_revision_latex(tex_content)
            if sanitized_tex_content != tex_content:
                tex_path.write_text(sanitized_tex_content, encoding="utf-8")
                changed = True
            if sanitized_revised_text and sanitized_revised_text != sanitized_tex_content:
                tex_path.write_text(sanitized_revised_text, encoding="utf-8")
                changed = True
        elif sanitized_revised_text:
            tex_path.write_text(sanitized_revised_text, encoding="utf-8")
            changed = True

        if changed:
            json_path.write_text(json.dumps(sanitized_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        sanitized_payload.setdefault("is_active_for_full_document", False)
        sanitized_payload.setdefault("created_at", "")
        sanitized_payload.setdefault("updated_at", "")
        sanitized_payload["json_path"] = str(json_path)
        sanitized_payload["tex_path"] = str(tex_path)
        return sanitized_payload

    def list_revision_drafts(self) -> list[dict[str, Any]]:
        drafts_dir = self.revision_drafts_dir
        items: list[dict[str, Any]] = []
        for json_path in sorted(drafts_dir.glob("*.json")):
            try:
                payload = json.loads(json_path.read_text(encoding="utf-8"))
                items.append(self._sanitize_draft_payload(json_path, payload))
            except json.JSONDecodeError:
                continue
        return items

    def load_revision_draft(self, json_path_value: str) -> dict[str, Any]:
        for item in self.list_revision_drafts():
            if item.get("json_path") == json_path_value:
                return item
        raise FileNotFoundError("Draft revisi tidak ditemukan.")

    def update_revision_draft_content(self, json_path_value: str, content: str) -> dict[str, Any]:
        json_path = Path(json_path_value)
        if not json_path.exists():
            raise FileNotFoundError("Draft revisi tidak ditemukan.")

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        sanitized_content = sanitize_revision_latex(content)
        payload["revised_text"] = sanitized_content
        payload["updated_at"] = datetime.now().isoformat()
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        json_path.with_suffix(".tex").write_text(sanitized_content, encoding="utf-8")
        return self._sanitize_draft_payload(json_path, payload)

    def list_active_revision_drafts(self) -> list[dict[str, Any]]:
        return [
            item
            for item in self.list_revision_drafts()
            if bool(item.get("is_active_for_full_document"))
        ]

    def _resolve_draft_unit_bounds(self, draft: dict[str, Any]) -> tuple[str, int, int]:
        selected_file = str(draft.get("selected_file", ""))
        selected_scope = str(draft.get("selected_scope", ""))
        selected_target_id = str(draft.get("selected_target_id", ""))

        if not selected_file or not selected_scope:
            raise ValueError("Metadata draft belum lengkap untuk penyusunan dokumen final.")

        source_path = self.thesis_root / selected_file
        if not source_path.exists():
            raise ValueError(f"File sumber draft tidak ditemukan: {selected_file}")

        document = parse_latex_structure(
            selected_file,
            source_path.read_text(encoding="utf-8"),
        )
        unit = resolve_review_unit(document, selected_scope, selected_target_id)
        return selected_file, int(unit["start_line"]), int(unit["end_line"])

    def _save_json_payload(self, json_path: Path, payload: dict[str, Any]) -> None:
        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def set_full_document_active(self, json_path_value: str, is_active: bool) -> dict[str, Any]:
        draft = self.load_revision_draft(json_path_value)
        json_path = Path(draft["json_path"])
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        payload["is_active_for_full_document"] = bool(is_active)
        payload["updated_at"] = datetime.now().isoformat()

        if is_active:
            target_file, target_start, target_end = self._resolve_draft_unit_bounds(draft)
            for other in self.list_revision_drafts():
                if other["json_path"] == draft["json_path"]:
                    continue
                if not other.get("is_active_for_full_document"):
                    continue

                other_file, other_start, other_end = self._resolve_draft_unit_bounds(other)
                overlaps = (
                    target_file == other_file
                    and target_start <= other_end
                    and other_start <= target_end
                )
                if not overlaps:
                    continue

                other_json_path = Path(other["json_path"])
                other_payload = json.loads(other_json_path.read_text(encoding="utf-8"))
                other_payload["is_active_for_full_document"] = False
                other_payload["updated_at"] = datetime.now().isoformat()
                self._save_json_payload(other_json_path, other_payload)

        self._save_json_payload(json_path, payload)
        return self._sanitize_draft_payload(json_path, payload)

    def delete_revision_draft(self, json_path_value: str) -> dict[str, str]:
        draft = self.load_revision_draft(json_path_value)
        json_path = Path(draft["json_path"])
        tex_path = Path(draft["tex_path"])

        if tex_path.exists():
            tex_path.unlink()
        if json_path.exists():
            json_path.unlink()

        return {
            "json_path": str(json_path),
            "tex_path": str(tex_path),
        }
