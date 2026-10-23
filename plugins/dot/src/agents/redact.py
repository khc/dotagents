import re
from typing import Any

# Specific token shapes first, then bearer tokens, then "name = value" credential assignments.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("stripe-key", re.compile(r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{8,}")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("api-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
]
KEY_BEGIN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
KEY_END = re.compile(r"-----END [A-Z ]*PRIVATE KEY-----")
BEARER = re.compile(r"(?P<head>\bBearer\s+)(?!\[REDACTED:)(?P<value>[A-Za-z0-9._~+/=-]{12,})", re.I)
# The match starts at the keyword, so the text before it stays outside the match and no unbounded identifier quantifier is needed
# (those backtrack quadratically on long hostile input). The suffix is bounded for the same reason.
NAME = r"(?:password|passwd|secret|token|api[_-]?key)[A-Za-z0-9_]{0,32}"
COUNTER_NAME = re.compile(r"^(?:max|min|num|count|total|limit)[_-]|tokens$|_(?:count|limit|max|min)$", re.I)  # token counts, not credentials
IDENTIFIER_TAIL = re.compile(r"[A-Za-z0-9_]*$")
QUOTED = re.compile(
    rf"""(?P<name>{NAME})(?P<nq>["']?)(?P<sep>\s*[:=]\s*)(?P<q>["'`])(?P<value>[^"'`\n]{{6,}})(?P=q)""",
    re.I,
)
UNQUOTED = re.compile(
    rf"""(?P<name>{NAME})(?P<sep>\s*[:=]\s*)(?!\[REDACTED:)(?P<value>[A-Za-z0-9_\-+/=.~]{{8,}})""",  # no trailing lookahead: a rejected match would be rescanned from every inner start
    re.I,
)
CODE_PATH = re.compile(r"^[A-Za-z_]+(\.[A-Za-z_]+)+$")  # process.env.TOKEN, os.environ.API_KEY: code, not a value
SKIPPED_KEYS = {"subject"}


def _is_counter(match: re.Match[str]) -> bool:
    start = match.start("name")
    head = IDENTIFIER_TAIL.search(match.string[max(0, start - 64):start])[0]
    counter_name = match["name"].lower().startswith("token") and COUNTER_NAME.search(head + match["name"])  # only tokens have counts
    return bool(counter_name) and match["value"].isdigit()  # and counts are numeric: ALLOWED_TOKENS=abc123 is a credential list


def _quoted(match: re.Match[str]) -> str:
    if match["value"].startswith("[REDACTED:") or _is_counter(match):
        return match.group(0)
    return f"{match['name']}{match['nq']}{match['sep']}{match['q']}[REDACTED:credential]{match['q']}"


def _unquoted(match: re.Match[str]) -> str:
    value = match["value"]
    if match.string[match.end():match.end() + 1] in ("(", "["):  # a call or an index: code, not a value
        return match.group(0)
    if CODE_PATH.match(value) or value.isalpha() or _is_counter(match):
        return match.group(0)  # code path or plain word (unquoted secrets almost always contain a digit or symbol), or a counter
    return f"{match['name']}{match['sep']}[REDACTED:credential]"


def _bearer(match: re.Match[str]) -> str:
    if match["value"].isalpha():  # prose such as "Bearer authentication"; real tokens contain a digit or symbol
        return match.group(0)
    return f"{match['head']}[REDACTED:bearer-token]"


def _redact_private_keys(text: str) -> str:
    """Replace each BEGIN..END block. Stops at the first header with no END (no later header can have one), so it is linear."""
    parts: list[str] = []
    pos = 0
    while (begin := KEY_BEGIN.search(text, pos)) and (end := KEY_END.search(text, begin.end())):
        parts += [text[pos:begin.start()], "[REDACTED:private-key]"]
        pos = end.end()
    return "".join(parts) + text[pos:]


def redact_secrets(text: str) -> str:
    """Replace credential values with [REDACTED:<type>], keeping names and positions."""
    text = _redact_private_keys(text)
    for kind, pattern in PATTERNS:
        text = pattern.sub(f"[REDACTED:{kind}]", text)
    text = BEARER.sub(_bearer, text)
    text = QUOTED.sub(_quoted, text)
    return UNQUOTED.sub(_unquoted, text)


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, dict):
        return {key: item if key in SKIPPED_KEYS else redact_value(item) for key, item in value.items()}
    return value
