from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from store_parity.browser import ActionError
from store_parity.browser.readiness import ReadinessResult
from store_parity.capture import CaptureBundle, ScreenshotSet
from store_parity.config import load_config
from store_parity.layout import RunLayout
from store_parity.runner import (
    AuditRunner,
    RunnerOptions,
    _consolidate_findings,
    _execute_steps_symmetrically,
)
from store_parity.issues import DetectorFinding, Severity
from store_parity.state import TaskStateStore


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class FakeTelemetry:
    def clear(self) -> None:
        pass


class FakePage:
    def __init__(self, url: str) -> None:
        self.url = url

    async def add_init_script(self, _script: str) -> None:
        pass

    async def content(self) -> str:
        return "<html><body><header></header><main></main><footer></footer></body></html>"


@dataclass
class FakeNavigation:
    requested_url: str


class FakeSession:
    def __init__(self, side: str, *, fail: bool = False) -> None:
        self.side = side
        self.page = FakePage(f"https://shop.example/{side}")
        self.telemetry = FakeTelemetry()
        self.navigations: list[FakeNavigation] = []
        self.fail = fail

    def requested_url(self, path: str) -> str:
        suffix = "?preview_theme_id=187054457141" if self.side == "preview" else ""
        return f"https://shop.example{path}{suffix}"

    async def navigate(self, path: str) -> FakeNavigation:
        if self.fail:
            raise RuntimeError(f"{self.side} navigation failed")
        navigation = FakeNavigation(self.requested_url(path))
        self.page.url = navigation.requested_url
        self.navigations.append(navigation)
        return navigation

    async def assert_theme_identity(self) -> str:
        return "187054457141" if self.side == "preview" else "live-theme"


class FakePair:
    def __init__(self, *, fail: bool = False) -> None:
        self.live = FakeSession("live", fail=fail)
        self.preview = FakeSession("preview", fail=fail)


class FakeRuntime:
    fail = False

    def __init__(self, _options: Any) -> None:
        self.pairs: list[FakePair] = []

    async def __aenter__(self) -> FakeRuntime:
        return self

    async def __aexit__(self, *_: Any) -> None:
        pass

    async def create_pair(self, _profile: Any) -> FakePair:
        pair = FakePair(fail=self.fail)
        self.pairs.append(pair)
        return pair

    async def close_pair(self, pair: FakePair) -> None:
        self.pairs.remove(pair)


async def fake_capture(
    page: FakePage,
    *,
    requested_url: str,
    **_: Any,
) -> CaptureBundle:
    landmark = {
        "selector": "fixture",
        "matches": [
            {
                "geometry": {
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 20,
                },
                "style": {"display": "block", "color": "rgb(0, 0, 0)"},
            }
        ],
    }
    return CaptureBundle(
        requested_url=requested_url,
        final_url=page.url,
        screenshots=ScreenshotSet(
            viewport=PNG,
            full_page=PNG,
            components={"header": PNG, "main": PNG, "footer": PNG},
        ),
        dom={
            "nodes": [
                {
                    "path": "main",
                    "tag": "main",
                    "text": "fixture",
                    "attributes": {},
                }
            ]
        },
        landmarks={
            "header": landmark,
            "main": landmark,
            "footer": landmark,
        },
        icons=(),
        overflow_offenders=(),
        console_errors=(),
        failed_first_party_requests=(),
        readiness=ReadinessResult(
            fonts_ready=True,
            font_checks={},
            visible_images=0,
            decoded_images=0,
            failed_images=(),
            stable_frames=3,
            pagefly="not_applicable",
            pagefly_selector=None,
        ),
    )


def default_config() -> Any:
    return load_config(Path(__file__).parents[1] / "config" / "default.yml")


@pytest.mark.asyncio
async def test_runner_executes_case_and_builds_registered_report(tmp_path: Path) -> None:
    layout = RunLayout.create(tmp_path / "runs", "orchestration")
    result = await AuditRunner(
        default_config(),
        layout,
        RunnerOptions(
            explicit_paths=("/",),
            max_representative_routes=1,
            max_cases=1,
        ),
        runtime_factory=FakeRuntime,
        capture_page_fn=fake_capture,
    ).run()

    assert result.status == "COMPLETE", result.error
    assert result.accepted is True
    assert result.case_counts == {"PASSED": 1}
    assert result.report_path is not None and result.report_path.is_file()
    manifest = json.loads(layout.manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "COMPLETE"
    assert manifest["artifact_ids"]
    assert "REPORT INCOMPLETO" not in result.report_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_optional_actions_skip_but_required_actions_fail() -> None:
    page = FakePage("https://shop.example/")
    optional = [{"action": "not-supported", "required": False}]
    live, preview = await _execute_steps_symmetrically(page, page, optional)
    assert live["0:not-supported"]["status"] == "skipped"
    assert preview["0:not-supported"]["status"] == "skipped"

    with pytest.raises(ActionError, match="required action"):
        await _execute_steps_symmetrically(
            page,
            page,
            [{"action": "not-supported", "required": True}],
        )


def test_repeated_findings_are_consolidated_without_losing_raw_count() -> None:
    findings = tuple(
        DetectorFinding(
            detector="dom-semantic",
            code="dom.semantic_mismatch",
            category="content",
            message="Semantic DOM content differs",
            severity=Severity.MAJOR,
            selector=f"main > div:nth-of-type({index})",
            exact_identity=True,
        )
        for index in range(25)
    )

    consolidated = _consolidate_findings(findings)

    assert len(consolidated) == 1
    assert consolidated[0].actual["occurrences"] == 25
    assert len(consolidated[0].actual["sample_selectors"]) == 10
    assert consolidated[0].exact_identity is True


@pytest.mark.asyncio
async def test_failed_run_is_inspectable_and_resume_retries_only_failure(
    tmp_path: Path,
) -> None:
    layout = RunLayout.create(tmp_path / "runs", "resume")
    FakeRuntime.fail = True
    failed = await AuditRunner(
        default_config(),
        layout,
        RunnerOptions(
            explicit_paths=("/",),
            max_representative_routes=1,
            max_cases=1,
            allow_incomplete_report=True,
        ),
        runtime_factory=FakeRuntime,
        capture_page_fn=fake_capture,
    ).run()
    assert failed.status == "FAILED"
    assert failed.report_path is not None and failed.report_path.is_file()
    assert "REPORT INCOMPLETO" in failed.report_path.read_text(encoding="utf-8")
    assert json.loads(layout.manifest_path.read_text(encoding="utf-8"))["artifact_ids"]

    FakeRuntime.fail = False
    resumed = await AuditRunner(
        default_config(),
        layout,
        RunnerOptions(profile="smoke", retry_failed=True),
        resume=True,
        runtime_factory=FakeRuntime,
        capture_page_fn=fake_capture,
    ).run()
    assert resumed.status == "COMPLETE", resumed.error
    assert resumed.case_counts == {"PASSED": 1}
    plan = json.loads(
        (layout.artifacts_dir / "metadata" / "audit-plan.json").read_text(
            encoding="utf-8"
        )
    )
    task = TaskStateStore(layout.state_db).get_task(plan["cases"][0]["id"])
    assert task is not None
    assert task.attempts == 4

