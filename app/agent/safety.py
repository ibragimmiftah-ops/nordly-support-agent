"""Deterministic input safety checks for untrusted ticket content."""

import re
import unicodedata
from dataclasses import dataclass

from app.observability.metrics import metrics

_INVISIBLE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")
_SPACE = re.compile(r"\s+")
_DIRECT_PATTERNS = (
    re.compile(r"\bignore\s+(?:all\s+)?(?:previous|prior|system)\s+instructions?\b"),
    re.compile(r"\b(?:reveal|show|print|repeat)\s+(?:the\s+)?system\s+prompt\b"),
    re.compile(r"\byou\s+are\s+now\b"),
    re.compile(r"\bdo\s+not\s+(?:escalate|follow)\b"),
)
_INDIRECT_PATTERNS = (
    re.compile(r"(?:^|\W)(?:system|assistant|developer)\s*:\s*"),
    re.compile(r"<\s*(?:system|assistant|instruction|prompt)\b"),
    re.compile(r"\[\s*(?:system|assistant|instruction|prompt)\s*\]"),
)


def normalize_untrusted_text(value: str) -> str:
    """Normalize Unicode and obfuscation before safety classification."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = _INVISIBLE.sub("", normalized)
    return _SPACE.sub(" ", normalized).strip()


@dataclass(frozen=True)
class SafetyFinding:
    """One deterministic safety classification."""

    kind: str
    severity: str
    matched_pattern: str


@dataclass(frozen=True)
class SafetyAssessment:
    """Safety assessment for a combined untrusted input."""

    normalized_text: str
    findings: tuple[SafetyFinding, ...]

    @property
    def blocked(self) -> bool:
        """Return whether human review is required."""
        return bool(self.findings)


class AgentSafetyMonitor:
    """Detect direct and indirect prompt injection deterministically."""

    def assess(self, *values: str | None) -> SafetyAssessment:
        """Normalize and assess ticket fields as one untrusted payload."""
        text = normalize_untrusted_text("\n".join(value or "" for value in values))
        findings: list[SafetyFinding] = []
        pattern_groups = (
            ("direct_injection", _DIRECT_PATTERNS),
            ("indirect_injection", _INDIRECT_PATTERNS),
        )
        for kind, patterns in pattern_groups:
            for pattern in patterns:
                if pattern.search(text):
                    finding = SafetyFinding(kind, "high", pattern.pattern)
                    findings.append(finding)
                    metrics.safety_events.labels(kind=kind, severity="high").inc()
                    break
        return SafetyAssessment(text, tuple(findings))
