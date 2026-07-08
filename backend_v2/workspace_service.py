import re
import shutil
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

from backend_v2.config import settings
from backend_v2.storage import LocalStorageAdapter


TEXT_EXTENSIONS = {".tex", ".bib", ".txt", ".md", ".sty", ".cls"}


def safe_relative_path(value: str) -> str:
    raw = value.replace("\\", "/").strip()
    if raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
        raise ValueError("Path workspace tidak valid.")
    normalized = raw.strip("/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise ValueError("Path workspace tidak valid.")
    return path.as_posix()


def create_blank_workspace(storage: LocalStorageAdapter, prefix: str) -> None:
    storage.write_text(
        f"{prefix}/main.tex",
        """\\documentclass[12pt,a4paper]{report}
\\usepackage[utf8]{inputenc}
\\usepackage[indonesian]{babel}
\\usepackage{graphicx}
\\usepackage{biblatex}
\\addbibresource{references.bib}

\\begin{document}
\\chapter{Pendahuluan}
Mulai menulis di sini.
\\printbibliography
\\end{document}
""",
    )
    storage.write_text(f"{prefix}/references.bib", "% Tambahkan referensi BibTeX di sini.\n")


def import_zip(storage: LocalStorageAdapter, prefix: str, content: bytes) -> None:
    archive_path = storage.write_bytes(f"{prefix}/.upload.zip", content)
    destination = storage.resolve(prefix)
    with zipfile.ZipFile(archive_path) as archive:
        for item in archive.infolist():
            relative = safe_relative_path(item.filename)
            target = (destination / relative).resolve()
            if not target.is_relative_to(destination):
                raise ValueError("ZIP berisi path yang tidak aman.")
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(item) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
    archive_path.unlink(missing_ok=True)


def list_workspace_files(root: Path) -> list[dict]:
    if not root.exists():
        return []
    items = []
    for path in sorted(root.rglob("*")):
        if path.name.startswith("."):
            continue
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            items.append({"path": relative, "size": 0, "editable": False, "kind": "folder"})
        elif path.is_file():
            items.append(
                {
                    "path": relative,
                    "size": path.stat().st_size,
                    "editable": path.suffix.lower() in TEXT_EXTENSIONS,
                    "kind": "file",
                }
            )
    return items


def _extract_compile_error(output: str) -> dict:
    summary = "Compile gagal."
    error_line = None
    error_context = ""

    for line in output.splitlines():
        cleaned = line.strip()
        if cleaned.startswith("! "):
            summary = cleaned[2:].strip() or summary
            continue
        match = re.match(r"l\.(\d+)\s?(.*)", cleaned)
        if match and error_line is None:
            error_line = int(match.group(1))
            error_context = match.group(2).strip()
            break

    return {"error_summary": summary, "error_line": error_line, "error_context": error_context}


def _run_latex_pipeline(cwd: Path, filename: str, stem: str) -> dict:
    commands = [
        ["xelatex", "-no-shell-escape", "-interaction=nonstopmode", filename],
        ["biber", stem],
        ["xelatex", "-no-shell-escape", "-interaction=nonstopmode", filename],
        ["xelatex", "-no-shell-escape", "-interaction=nonstopmode", filename],
    ]
    steps = []
    for index, command in enumerate(commands):
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=settings.compile_timeout_seconds,
        )
        steps.append({"name": command[0], "returncode": completed.returncode})
        if completed.returncode != 0:
            if index == 1 and "Cannot find" in ((completed.stdout or "") + (completed.stderr or "")):
                continue
            output = (completed.stdout or "") + "\n" + (completed.stderr or "")
            details = _extract_compile_error(output)
            return {"success": False, "steps": steps, "pdf_path": "", **details}
    pdf_path = cwd / f"{stem}.pdf"
    return {"success": pdf_path.exists(), "steps": steps, "pdf_path": str(pdf_path) if pdf_path.exists() else ""}


def _apply_workspace_tex_fixes(output_root: Path) -> None:
    for candidate in output_root.rglob("*.tex"):
        content = candidate.read_text(encoding="utf-8")
        if r"\usepackage{newtxtext,newtxmath}" in content:
            candidate.write_text(content.replace(r"\usepackage{newtxtext,newtxmath}", r"\usepackage{mathptmx}"), encoding="utf-8")


def compile_workspace(workspace_root: Path, main_document: str, output_root: Path) -> dict:
    safe_main = safe_relative_path(main_document)
    source_main = (workspace_root / safe_main).resolve()
    if not source_main.is_relative_to(workspace_root.resolve()) or not source_main.exists():
        raise ValueError("Main document tidak ditemukan.")
    if output_root.exists():
        shutil.rmtree(output_root)
    shutil.copytree(workspace_root, output_root)
    main_path = output_root / safe_main
    _apply_workspace_tex_fixes(output_root)
    return _run_latex_pipeline(main_path.parent, main_path.name, main_path.stem)


def compile_workspace_file(workspace_root: Path, target_path: str, output_root: Path) -> dict:
    safe_target = safe_relative_path(target_path)
    source_target = (workspace_root / safe_target).resolve()
    if not source_target.is_relative_to(workspace_root.resolve()) or not source_target.exists():
        raise ValueError("File target tidak ditemukan.")
    if source_target.suffix.lower() != ".tex":
        raise ValueError("Hanya file .tex yang bisa di-compile langsung.")

    if output_root.exists():
        shutil.rmtree(output_root)
    shutil.copytree(workspace_root, output_root)
    _apply_workspace_tex_fixes(output_root)

    compile_target = output_root / safe_target
    content = compile_target.read_text(encoding="utf-8")

    if r"\documentclass" in content:
        entry_path = compile_target
    else:
        wrapper_path = output_root / "__single_file_preview__.tex"
        preamble_path = output_root / "preamble.tex"
        if preamble_path.exists():
            preamble_block = r"\input{preamble.tex}"
        else:
            fallback = [
                r"\usepackage[utf8]{inputenc}",
                r"\usepackage[indonesian]{babel}",
                r"\usepackage{graphicx}",
            ]
            if (output_root / "references.bib").exists():
                fallback.extend([r"\usepackage{biblatex}", r"\addbibresource{references.bib}"])
            preamble_block = "\n".join(fallback)
        input_target = PurePosixPath(safe_target).with_suffix("").as_posix()
        wrapper = f"""\\documentclass[12pt,a4paper]{{report}}
{preamble_block}

\\begin{{document}}
\\input{{{input_target}}}
\\end{{document}}
"""
        wrapper_path.write_text(wrapper, encoding="utf-8")
        entry_path = wrapper_path

    result = _run_latex_pipeline(entry_path.parent, entry_path.name, entry_path.stem)
    result["compiled_path"] = safe_target
    return result


def _font_package(font_family: str) -> tuple[str, str]:
    family = (font_family or "times").strip().lower()
    if family == "palatino":
        return r"\usepackage{mathpazo}", "Palatino"
    if family == "helvetica":
        return r"""\usepackage[scaled]{helvet}
\renewcommand{\familydefault}{\sfdefault}""", "Helvetica"
    return r"\usepackage{mathptmx}", "Times"


def _chapter_heading(chapter_style: str) -> str:
    style = (chapter_style or "default").strip().lower()
    if style == "simple":
        return r"\titleformat{\chapter}[display]{\bfseries\Large}{BAB \thechapter}{0.5em}{\centering\Large}"
    if style == "centered":
        return r"\titleformat{\chapter}[display]{\bfseries\huge}{BAB \thechapter}{0.6em}{\centering\Huge}"
    return r"\titleformat{\chapter}[display]{\bfseries\Large}{BAB \thechapter}{0.75em}{\Large}"


def build_workspace_scaffold(config: dict) -> dict[str, str]:
    font_package, font_label = _font_package(str(config.get("font_family", "times")))
    chapter_heading = _chapter_heading(str(config.get("chapter_style", "default")))
    line_spacing = str(config.get("line_spacing", "1.5"))
    bibliography_style = str(config.get("bibliography_style", "numeric"))
    include_cover = bool(config.get("include_cover", True))
    cover_include = "\\input{cover.tex}\n" if include_cover else ""
    cover_file = "" if not include_cover else """\\begin{titlepage}
\\centering
{\\Large Judul Skripsi Anda\\par}
\\vspace{1.5cm}
{\\large Nama Mahasiswa\\par}
\\vfill
Program Studi\\par
Universitas\\par
\\the\\year
\\end{titlepage}
"""
    preamble = f"""\\usepackage[utf8]{{inputenc}}
\\usepackage[indonesian]{{babel}}
\\usepackage{{geometry}}
\\geometry{{top={config.get('margin_top_cm', 4)}cm,right={config.get('margin_right_cm', 3)}cm,bottom={config.get('margin_bottom_cm', 3)}cm,left={config.get('margin_left_cm', 4)}cm}}
\\usepackage{{graphicx}}
\\usepackage{{setspace}}
\\setstretch{{{line_spacing}}}
{font_package}
\\usepackage{{titlesec}}
{chapter_heading}
\\usepackage{{csquotes}}
\\usepackage[backend=biber,style={bibliography_style}]{{biblatex}}
\\addbibresource{{references.bib}}
"""
    main_tex = f"""\\documentclass[{config.get('font_size', '12pt')},{config.get('paper_size', 'a4paper')}]{{report}}
\\input{{preamble.tex}}

\\begin{{document}}
{cover_include}\\tableofcontents
\\input{{chapters/01-pendahuluan.tex}}
\\printbibliography
\\end{{document}}
"""
    chapter_file = """\\chapter{Pendahuluan}
Tulis isi bab di sini.
"""
    readme = f"""Workspace ini dibuat otomatis dari form layout Thesis Atelier.

Pengaturan aktif:
- Font: {font_label}
- Ukuran font: {config.get('font_size', '12pt')}
- Kertas: {config.get('paper_size', 'a4paper')}
- Spasi: {line_spacing}
- Margin: atas {config.get('margin_top_cm', 4)} cm, kanan {config.get('margin_right_cm', 3)} cm, bawah {config.get('margin_bottom_cm', 3)} cm, kiri {config.get('margin_left_cm', 4)} cm

File penting:
- main.tex
- preamble.tex
- cover.tex
- chapters/01-pendahuluan.tex
- references.bib
"""
    return {
        "main.tex": main_tex,
        "preamble.tex": preamble,
        "cover.tex": cover_file,
        "chapters/01-pendahuluan.tex": chapter_file,
        "references.bib": "% Tambahkan referensi BibTeX di sini.\n",
        "README_WORKSPACE.txt": readme,
    }


def create_scaffold_workspace(storage: LocalStorageAdapter, prefix: str, config: dict) -> None:
    for relative, content in build_workspace_scaffold(config).items():
        storage.write_text(f"{prefix}/{relative}", content)


def build_workspace_snippet(config: dict) -> dict[str, str]:
    scaffold = build_workspace_scaffold(config)
    return {
        "preamble.tex": scaffold["preamble.tex"],
        "main.tex": scaffold["main.tex"],
        "cover.tex": scaffold["cover.tex"],
        "chapter_example.tex": scaffold["chapters/01-pendahuluan.tex"],
        "instruction": "Masukkan kode preamble ke file preamble/template Anda. Jika belum punya cover, pakai isi cover.tex. Untuk bab awal, Anda bisa mulai dari chapter_example.tex.",
    }
