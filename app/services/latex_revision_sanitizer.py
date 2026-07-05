import re


def sanitize_revision_latex(text: str) -> str:
    sanitized = text.replace("\r\n", "\n")

    # Convert simple markdown bold that sometimes slips out of the LLM.
    sanitized = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", sanitized)

    # Escape bare ampersands that would break LaTeX outside alignment environments.
    sanitized = re.sub(r"(?<!\\)&", r"\\&", sanitized)

    # Normalize a few characters that often appear garbled in copied model output.
    sanitized = sanitized.replace("‑", "-")
    sanitized = sanitized.replace("–", "-")
    sanitized = sanitized.replace("—", "-")

    return sanitized.strip()
