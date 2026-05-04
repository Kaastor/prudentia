from __future__ import annotations

import re

SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{8,}"), "sk-***"),
    (re.compile(r"OPENAI_API_KEY\s*[:=]\s*[^\s]+", re.IGNORECASE), "OPENAI_API_KEY=***"),
    (re.compile(r"(?i)(password|token|secret|session)[_\- ]?(key|token|id)?\s*[:=]\s*[^\s]+"), r"\1=***"),
    (re.compile(r"~/.codex/auth\.json"), "~/.codex/auth.json(redacted-path)"),
]


def redact_text(value: str) -> str:
    redacted = value
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted
