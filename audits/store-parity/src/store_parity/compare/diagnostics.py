from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

from store_parity.issues import DetectorFinding, Severity


_VOLATILE = re.compile(
    r"\b(?:[a-f0-9]{12,}|\d{10,}|https?://[^/\s]+)", re.IGNORECASE
)


def _message(entry: Mapping[str, Any]) -> str:
    return " ".join(
        str(
            entry.get(
                "message",
                entry.get("text", entry.get("error", entry.get("failure", ""))),
            )
        ).split()
    )


def _console_key(entry: Mapping[str, Any]) -> tuple[str, str]:
    level = str(entry.get("type", entry.get("level", "log"))).lower()
    return level, _VOLATILE.sub("*", _message(entry))


def _request_path(entry: Mapping[str, Any]) -> str:
    url = str(entry.get("url", entry.get("request_url", "")))
    parsed = urlsplit(url)
    return parsed.path or url


def _network_key(entry: Mapping[str, Any]) -> tuple[str, str, int, str]:
    return (
        str(entry.get("method", "GET")).upper(),
        _request_path(entry),
        int(entry.get("status", 0) or 0),
        _VOLATILE.sub("*", _message(entry)),
    )


@dataclass(frozen=True, slots=True)
class DiagnosticComparison:
    passed: bool
    findings: tuple[DetectorFinding, ...]
    console_errors: int
    network_errors: int


def compare_diagnostics(
    baseline_console: Iterable[Mapping[str, Any]] = (),
    candidate_console: Iterable[Mapping[str, Any]] = (),
    baseline_network: Iterable[Mapping[str, Any]] = (),
    candidate_network: Iterable[Mapping[str, Any]] = (),
    *,
    ignored_message_patterns: Sequence[str] = (),
) -> DiagnosticComparison:
    ignored = tuple(re.compile(pattern) for pattern in ignored_message_patterns)
    baseline_console_keys = {_console_key(entry) for entry in baseline_console}
    baseline_network_keys = {_network_key(entry) for entry in baseline_network}
    findings: list[DetectorFinding] = []
    console_errors = 0
    network_errors = 0

    for entry in candidate_console:
        key = _console_key(entry)
        level, message = key
        if (
            level not in {"error", "assert"}
            or key in baseline_console_keys
            or any(pattern.search(message) for pattern in ignored)
        ):
            continue
        console_errors += 1
        findings.append(
            DetectorFinding(
                detector="console",
                code="runtime.console_error",
                category="runtime",
                message=f"New browser console {level}: {message}",
                severity=Severity.MAJOR,
                actual=dict(entry),
                metadata={"fingerprint_fields": {"message": message}},
            )
        )

    for entry in candidate_network:
        key = _network_key(entry)
        method, path, status, failure = key
        is_failure = bool(failure) or status >= 400
        if not is_failure or key in baseline_network_keys:
            continue
        network_errors += 1
        findings.append(
            DetectorFinding(
                detector="network",
                code=(
                    "runtime.network_failure"
                    if failure and not status
                    else "runtime.http_error"
                ),
                category="runtime",
                message=(
                    f"New network failure for {method} {path}: "
                    f"{failure or status}"
                ),
                severity=Severity.CRITICAL if status >= 500 else Severity.MAJOR,
                actual=dict(entry),
                metadata={
                    "request": f"{method} {path}",
                    "status": status,
                },
            )
        )

    return DiagnosticComparison(
        passed=not findings,
        findings=tuple(findings),
        console_errors=console_errors,
        network_errors=network_errors,
    )


diagnose_console_and_network = compare_diagnostics
