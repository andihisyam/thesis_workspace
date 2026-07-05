from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def sync_figures(thesis_root: Path, project_root: Path) -> None:
    thesis_figures = thesis_root / "figures"
    thesis_figures.mkdir(parents=True, exist_ok=True)
    fallback_figures = project_root / "figures"
    if not fallback_figures.exists():
        return

    for file in fallback_figures.iterdir():
        if file.is_file():
            target = thesis_figures / file.name
            if not target.exists():
                shutil.copy2(file, target)


def _collect_log_summary(log_path: Path) -> str:
    if not log_path.exists():
        return "File log compile belum ditemukan."

    lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    errors = [line.strip() for line in lines if line.lstrip().startswith("!")]
    warnings = [line.strip() for line in lines if "Warning" in line]

    parts: list[str] = []
    if errors:
        parts.append("Error utama: " + " | ".join(errors[:5]))
    if warnings:
        parts.append("Warning penting: " + " | ".join(warnings[:5]))
    if not parts:
        parts.append("Compile selesai tanpa error atau warning utama yang terdeteksi dari parser sederhana.")
    return "\n".join(parts)


def run_latex_compile(thesis_root: Path, project_root: Path) -> dict:
    sync_figures(thesis_root, project_root)
    commands = [
        ("XeLaTeX pass 1", ["xelatex", "-interaction=nonstopmode", "main.tex"]),
        ("Biber", ["biber", "main"]),
        ("XeLaTeX pass 2", ["xelatex", "-interaction=nonstopmode", "main.tex"]),
        ("XeLaTeX pass 3", ["xelatex", "-interaction=nonstopmode", "main.tex"]),
    ]

    steps: list[dict] = []
    success = True
    for name, command in commands:
        completed = subprocess.run(
            command,
            cwd=thesis_root,
            capture_output=True,
            text=True,
            timeout=180,
        )
        step = {
            "name": name,
            "command": " ".join(command),
            "returncode": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }
        steps.append(step)
        if completed.returncode != 0:
            success = False
            break

    log_path = thesis_root / "main.log"
    pdf_path = thesis_root / "main.pdf"
    summary = _collect_log_summary(log_path)

    return {
        "success": success and pdf_path.exists(),
        "steps": steps,
        "summary": summary,
        "log_path": str(log_path),
        "pdf_path": str(pdf_path) if pdf_path.exists() else "",
    }
