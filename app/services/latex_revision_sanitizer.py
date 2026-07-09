import re

COMMANDS = (
    "chapter",
    "section",
    "subsection",
    "subsubsection",
    "begin",
    "end",
    "item",
    "caption",
    "label",
    "input",
    "include",
    "includegraphics",
    "cite",
    "parencite",
    "textcite",
    "ref",
    "eqref",
)


def _escape_bare_ampersands(text: str) -> str:
    return re.sub(r"(?<!\)&", r"\&", text)


def _escape_bare_percent(text: str) -> str:
    return re.sub(r"(?<!\)%", r"\%", text)


def _escape_bare_hash(text: str) -> str:
    return re.sub(r"(?<!\)#", r"\#", text)


def _escape_bare_underscore(text: str) -> str:
    return re.sub(r"(?<!\)_", r"\_", text)


def _normalize_numeric_ranges(text: str) -> str:
    return re.sub(r"(?<=\d)-(?=\d)", "--", text)


def _repair_missing_leading_backslash(text: str) -> str:
    pattern = re.compile(rf"^(?P<indent>\s*)(?P<cmd>{'|'.join(COMMANDS)})\b", re.MULTILINE)
    return pattern.sub(lambda m: f"{m.group('indent')}\\{m.group('cmd')}", text)


def sanitize_revision_latex(text: str) -> str:
    if not text:
        return text
    value = text.replace("\r\n", "\n")
    value = _repair_missing_leading_backslash(value)
    value = _normalize_numeric_ranges(value)
    value = _escape_bare_ampersands(value)
    value = _escape_bare_percent(value)
    value = _escape_bare_hash(value)
    value = _escape_bare_underscore(value)
    return value
