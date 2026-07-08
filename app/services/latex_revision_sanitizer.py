import re


def sanitize_revision_latex(text: str) -> str:
    sanitized = text.replace("\r\n", "\n")

    # Convert simple markdown bold that sometimes slips out of the LLM.
    sanitized = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", sanitized)

    # Escape common LaTeX special characters when they appear as plain text.
    sanitized = re.sub(r"(?<!\\)&", r"\\&", sanitized)
    sanitized = re.sub(r"(?<!\\)%", r"\\%", sanitized)
    sanitized = re.sub(r"(?<!\\)#", r"\\#", sanitized)
    sanitized = re.sub(r"(?<!\\)_", r"\\_", sanitized)

    sanitized = re.sub(
        r"(?m)^(\s*)(chapter|section|subsection|subsubsection|begin|end|item|caption|label|input|include|includegraphics|cite|parencite|textcite|ref)\b",
        r"\1\\\2",
        sanitized,
    )

    # Normalize repeated hyphens often used as numeric ranges in copied table labels.
    sanitized = re.sub(r"(?<=\d)-(?![\s\-])(?=\d)", "--", sanitized)

    # Normalize a few characters that often appear garbled in copied model output.
    sanitized = sanitized.replace("‑", "-")
    sanitized = sanitized.replace("–", "-")
    sanitized = sanitized.replace("—", "-")

    return sanitized.strip()
