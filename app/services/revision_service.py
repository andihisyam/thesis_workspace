from __future__ import annotations

from typing import Iterable


def build_revision_draft(source_text: str, suggestions: Iterable[dict], section_label: str, user_goal: str) -> tuple[str, str]:
    clean_text = source_text.strip()
    suggestions = list(suggestions)
    notes: list[str] = []
    for index, item in enumerate(suggestions[:8], start=1):
        issue = str(item.get("issue", "")).strip()
        suggestion = str(item.get("suggestion", "")).strip()
        if not issue and not suggestion:
            continue
        notes.append(f"{index}. {issue} {suggestion}".strip())

    if not notes:
        summary = f"Draft {section_label} dibuat dari teks sumber tanpa perubahan otomatis besar. Tujuan user: {user_goal}."
        return clean_text, summary

    appendix = "\n\n% Catatan revisi otomatis\n" + "\n".join(f"% {line}" for line in notes)
    summary = f"Draft {section_label} dibuat dengan {len(notes)} catatan revisi. Tujuan user: {user_goal}."
    return clean_text + appendix, summary
