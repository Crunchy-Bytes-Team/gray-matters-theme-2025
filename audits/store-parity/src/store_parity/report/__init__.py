"""Static, registry-backed HTML reporting for store parity runs."""

from store_parity.report.builder import (
    ReportBuildError,
    ReportBuilder,
    ReportResult,
    build_report,
    validate_report_links,
)

__all__ = [
    "ReportBuildError",
    "ReportBuilder",
    "ReportResult",
    "build_report",
    "validate_report_links",
]
