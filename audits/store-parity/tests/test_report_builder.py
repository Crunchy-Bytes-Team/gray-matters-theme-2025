from __future__ import annotations

import json
from pathlib import Path

import pytest

from store_parity.artifacts import ArtifactRegistry
from store_parity.layout import RunLayout
from store_parity.manifest import ManifestLifecycle
from store_parity.models import ArtifactKind
from store_parity.report import (
    ReportBuildError,
    build_report,
    validate_report_links,
)
from store_parity.state import TaskStateStore


@pytest.fixture
def report_run(tmp_path: Path) -> tuple[RunLayout, ArtifactRegistry, dict[str, str]]:
    layout = RunLayout.create(tmp_path / "runs", "report-fixture")
    state = TaskStateStore(layout.state_db)
    registry = ArtifactRegistry(layout, state)
    lifecycle = ManifestLifecycle(layout, registry, state)
    lifecycle.start(config_digest="a" * 64, profile="smoke")
    lifecycle.mark_running()

    live = registry.register_bytes(
        "captures/home-live.png",
        b"registered-live-image",
        kind=ArtifactKind.SCREENSHOT,
        media_type="image/png",
        metadata={"role": "live"},
    )
    preview = registry.register_bytes(
        "captures/home-preview.png",
        b"registered-preview-image",
        kind=ArtifactKind.SCREENSHOT,
        media_type="image/png",
        metadata={"role": "preview"},
    )
    diff = registry.register_bytes(
        "diffs/home-diff.png",
        b"registered-diff-image",
        kind=ArtifactKind.DIFF,
        media_type="image/png",
        metadata={"role": "diff"},
    )
    trace = registry.register_bytes(
        "logs/home-trace.zip",
        b"registered-trace",
        kind=ArtifactKind.LOG,
        media_type="application/zip",
        metadata={"role": "trace"},
    )
    document = {
        "pages": [
            {
                "id": "home",
                "url": "https://www.example.test/",
                "path": "/",
                "page_type": "home",
                "source": "seed",
                "metadata": {"preview_url": "https://preview.example.test/"},
            }
        ],
        "case_results": [
            {
                "id": "home-mobile",
                "page_id": "home",
                "profile": "smoke",
                "scenario": "Navigazione primaria",
                "viewport": {"width": 390, "height": 844},
                "status": "FAILED",
                "artifact_ids": [live.id, preview.id, diff.id, trace.id],
                "metrics": {"pixel_ratio": 0.12},
            }
        ],
        "issues": [
            {
                "id": "issue-header",
                "case_result_id": "home-mobile",
                "category": "visual",
                "severity": "major",
                "title": "Header non allineato",
                "description": "Il logo preview è spostato rispetto allo store live.",
                "selector": ".site-header",
                "artifact_ids": [live.id, preview.id, diff.id, trace.id],
            }
        ],
        "features": [
            {
                "id": "navigation",
                "name": "Navigazione primaria",
                "description": "Header e menu principale.",
            }
        ],
    }
    report_data = registry.register_json(
        "metadata/report-data.json",
        document,
        metadata={"report_role": "report_data"},
    )
    lifecycle.complete([live.id, preview.id, diff.id, trace.id, report_data.id])
    return layout, registry, {
        "live": live.id,
        "preview": preview.id,
        "data": report_data.id,
    }


def test_builds_navigable_report_from_registered_manifest_only(
    report_run: tuple[RunLayout, ArtifactRegistry, dict[str, str]],
) -> None:
    layout, registry, _ = report_run
    stale = layout.artifacts_dir / "metadata" / "stale.json"
    stale.write_text(
        json.dumps(
            {
                "issues": [
                    {
                        "id": "stale-issue",
                        "title": "NON DEVE APPARIRE",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = build_report(registry)

    assert result.incomplete is False
    assert result.index_path.is_file()
    assert (result.output_dir / "coverage.html").is_file()
    assert (result.output_dir / "routes" / "home.html").is_file()
    assert (result.output_dir / "features" / "navigation.html").is_file()
    assert (result.output_dir / "issues" / "issue-header.html").is_file()
    assert (result.output_dir / "data" / "issues" / "issue-header.json").is_file()
    all_html = "\n".join(
        path.read_text(encoding="utf-8")
        for path in result.generated_files
        if path.suffix == ".html"
    )
    assert "NON DEVE APPARIRE" not in all_html
    assert "Header non allineato" in all_html
    assert 'href="features/navigation.html"' in all_html
    assert "data-view-mode=\"slider\"" in all_html
    assert "data-view-mode=\"diff\"" in all_html
    assert "Apri live" in all_html
    assert "JSON grezzo" in all_html
    report_js = (result.output_dir / "assets" / "report.js").read_text(encoding="utf-8")
    assert "getAttribute(`data-${key}`)" in report_js
    validate_report_links(result.output_dir, allowed_root=layout.root)


def test_missing_registered_artifact_fails_report_build(
    report_run: tuple[RunLayout, ArtifactRegistry, dict[str, str]],
) -> None:
    _, registry, ids = report_run
    registry.resolve(ids["live"]).unlink()

    with pytest.raises(ReportBuildError, match="artifact manifest non valido"):
        build_report(registry)


def test_incomplete_manifest_requires_opt_in_and_shows_banner(
    report_run: tuple[RunLayout, ArtifactRegistry, dict[str, str]],
    tmp_path: Path,
) -> None:
    layout, registry, _ = report_run
    manifest = json.loads(layout.manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "RUNNING"
    manifest.pop("completed_at")
    manifest["task_summary"] = {"RUNNING": 1}

    with pytest.raises(ReportBuildError, match="allow_incomplete=True"):
        build_report(
            registry,
            manifest=manifest,
            output_dir=tmp_path / "refused-report",
        )

    result = build_report(
        registry,
        manifest=manifest,
        output_dir=layout.root / "incomplete-report",
        allow_incomplete=True,
    )
    assert result.incomplete is True
    assert "REPORT INCOMPLETO" in result.index_path.read_text(encoding="utf-8")


def test_broken_internal_link_validation_is_rejected(
    report_run: tuple[RunLayout, ArtifactRegistry, dict[str, str]],
) -> None:
    layout, registry, _ = report_run
    result = build_report(registry)
    with result.index_path.open("a", encoding="utf-8") as stream:
        stream.write('<a href="issues/non-esiste.html">rotto</a>')

    with pytest.raises(ReportBuildError, match="link mancante"):
        validate_report_links(result.output_dir, allowed_root=layout.root)
