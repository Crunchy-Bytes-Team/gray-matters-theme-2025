"""End-to-end orchestration for live-versus-preview store parity audits."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import urllib.request
import uuid
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

from store_parity.artifacts import Artifact, ArtifactRegistry
from store_parity.browser import (
    ActionError,
    BrowserProfile,
    BrowserRuntime,
    ReadinessOptions,
    RuntimeOptions,
    StoreActions,
)
from store_parity.capture import CaptureBundle, CaptureOptions, capture_page
from store_parity.compare import (
    compare_accessibility_issues,
    compare_behavior_contracts,
    compare_computed_styles,
    compare_diagnostics,
    compare_dom_semantics,
    compare_geometry,
    compare_icons,
    compare_images,
)
from store_parity.config import LoadedConfig
from store_parity.inventory import (
    DiscoveryLimits,
    InventoryDiscoverer,
    canonicalize_url,
    classify_page_type,
    classify_template,
    enrich_page_from_rendered_html,
    feature_signature,
)
from store_parity.issues import (
    ClassifiedIssue,
    DetectorFinding,
    IssueStatus,
    Severity,
    classify_findings,
    evaluate_acceptance_gate,
)
from store_parity.layout import RunLayout
from store_parity.manifest import ManifestLifecycle
from store_parity.models import ArtifactKind, CaseStatus, Page, TaskStatus, isoformat, utc_now
from store_parity.report import ReportBuilder
from store_parity.scenarios import ScenarioPlanner
from store_parity.state import Task, TaskStateStore


FetchText = Callable[[str], str]
CapturePage = Callable[..., Awaitable[CaptureBundle]]
RuntimeFactory = Callable[[RuntimeOptions], Any]


@dataclass(frozen=True, slots=True)
class RunnerOptions:
    profile: str = "smoke"
    explicit_paths: tuple[str, ...] = ()
    max_representative_routes: int | None = None
    max_cases: int | None = None
    retry_failed: bool = False
    allow_incomplete_report: bool = False

    def __post_init__(self) -> None:
        if self.max_representative_routes is not None and self.max_representative_routes <= 0:
            raise ValueError("max_representative_routes must be positive")
        if self.max_cases is not None and self.max_cases <= 0:
            raise ValueError("max_cases must be positive")


@dataclass(frozen=True, slots=True)
class RunResult:
    run_id: str
    run_dir: Path
    status: str
    report_path: Path | None
    accepted: bool
    case_counts: Mapping[str, int]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "status": self.status,
            "report_path": str(self.report_path) if self.report_path else None,
            "accepted": self.accepted,
            "case_counts": dict(self.case_counts),
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class _CaseOutcome:
    case: Mapping[str, Any]
    page: Mapping[str, Any]
    result: Mapping[str, Any]
    issues: tuple[Mapping[str, Any], ...]
    classified: tuple[ClassifiedIssue, ...]
    evidence_ids: tuple[str, ...]

    def to_document(self) -> dict[str, Any]:
        return {
            "page": dict(self.page),
            "case_result": dict(self.result),
            "issues": [dict(item) for item in self.issues],
            "evidence_ids": list(self.evidence_ids),
            "classified_issues": [item.to_dict() for item in self.classified],
        }


class AuditRunner:
    """Coordinate discovery, paired browser evidence, comparisons, and reporting."""

    def __init__(
        self,
        config: LoadedConfig,
        layout: RunLayout,
        options: RunnerOptions,
        *,
        resume: bool = False,
        fetch_text: FetchText | None = None,
        runtime_factory: RuntimeFactory = BrowserRuntime,
        capture_page_fn: CapturePage = capture_page,
    ) -> None:
        self.config = config
        self.layout = layout
        self.options = options
        self.resume = resume
        self.state = TaskStateStore(layout.state_db)
        self.registry = ArtifactRegistry(layout, self.state)
        self.manifest = ManifestLifecycle(layout, self.registry, self.state)
        self.fetch_text = fetch_text or _fetch_text
        self.runtime_factory = runtime_factory
        self.capture_page = capture_page_fn

    async def run(self) -> RunResult:
        report_path: Path | None = None
        selected_ids: tuple[str, ...] = ()
        try:
            await self._prepare_manifest()
            plan = self._load_plan() if self.resume else None
            if plan is None:
                plan = self._discover_and_plan()
            self._prepare_tasks(plan)
            if self.resume:
                self.state.prepare_resume(retry_failed=self.options.retry_failed)

            await self._execute_pending_cases()
            outcomes = self._load_latest_outcomes()
            report_data, selected_ids, accepted = self._aggregate(plan, outcomes)
            _validate_report_records(report_data)
            data_artifact = self.registry.register_json(
                f"metadata/report-data-{uuid.uuid4().hex[:12]}.json",
                report_data,
                metadata={"report_role": "report_data"},
            )
            selected_ids = tuple(dict.fromkeys((*selected_ids, data_artifact.id)))

            failed_tasks = self.state.counts().get(TaskStatus.FAILED.value, 0)
            if failed_tasks:
                self.manifest.fail(selected_ids)
                if self.options.allow_incomplete_report:
                    report_path = ReportBuilder(
                        self.registry,
                        manifest=self.manifest.read(),
                        allow_incomplete=True,
                    ).build().index_path
                return RunResult(
                    run_id=self.layout.run_id,
                    run_dir=self.layout.root,
                    status="FAILED",
                    report_path=report_path,
                    accepted=False,
                    case_counts=_case_counts(outcomes),
                    error=f"{failed_tasks} case task(s) failed",
                )

            # Reports are derived output under run/report, not immutable registry
            # artifacts. Build and link-check against a prospective COMPLETE
            # manifest first, then commit the immutable manifest as the last step.
            prospective = {
                **self.manifest.read(),
                "status": "COMPLETE",
                "completed_at": isoformat(utc_now()),
                "artifact_ids": list(selected_ids),
                "task_summary": self.state.counts(),
            }
            report_result = ReportBuilder(
                self.registry,
                manifest=prospective,
            ).build()
            try:
                self.manifest.complete(selected_ids)
            except Exception:
                shutil.rmtree(report_result.output_dir, ignore_errors=True)
                raise
            report_path = report_result.index_path
            return RunResult(
                run_id=self.layout.run_id,
                run_dir=self.layout.root,
                status="COMPLETE",
                report_path=report_path,
                accepted=accepted,
                case_counts=_case_counts(outcomes),
            )
        except Exception as error:
            try:
                if self.layout.manifest_path.is_file():
                    self.manifest.fail(selected_ids)
                    if self.options.allow_incomplete_report:
                        report_path = ReportBuilder(
                            self.registry,
                            manifest=self.manifest.read(),
                            allow_incomplete=True,
                        ).build().index_path
            except Exception:
                report_path = None
            return RunResult(
                run_id=self.layout.run_id,
                run_dir=self.layout.root,
                status="FAILED",
                report_path=report_path,
                accepted=False,
                case_counts={},
                error=f"{type(error).__name__}: {error}",
            )

    async def _prepare_manifest(self) -> None:
        if not self.resume:
            self.manifest.start(
                config_digest=self.config.digest,
                profile=self.options.profile,
            )
            self.manifest.mark_running()
            return
        value = self.manifest.read()
        if value.get("status") == "COMPLETE":
            raise RuntimeError("a COMPLETE run cannot be resumed")
        if value.get("config_digest") != self.config.digest:
            raise RuntimeError("resume config digest does not match the original run")
        if value.get("profile") != self.options.profile:
            raise RuntimeError("resume profile does not match the original run")
        self.manifest.resume()

    def _discover_and_plan(self) -> dict[str, Any]:
        config = self.config.mutable_copy()
        live_url = str(config["targets"]["live"]["base_url"])
        if self.options.explicit_paths:
            pages = tuple(
                _manual_page(live_url, value)
                for value in dict.fromkeys(self.options.explicit_paths)
            )
            inventory_document = {
                "pages": [page.to_dict() for page in pages],
                "sitemap_urls": [],
                "truncated": False,
                "errors": [],
                "mode": "explicit_paths",
            }
        else:
            runtime = config.get("runtime", {})
            limits = DiscoveryLimits(
                max_sitemaps=int(runtime.get("discovery_max_sitemaps", 100)),
                max_pages=int(runtime.get("discovery_max_pages", 10_000)),
                max_link_pages=int(runtime.get("discovery_max_link_pages", 25)),
                max_links_per_page=int(runtime.get("discovery_max_links_per_page", 100)),
            )
            inventory = InventoryDiscoverer(
                live_url,
                self.fetch_text,
                limits=limits,
                random_seed=self.layout.run_id,
            ).discover()
            pages = inventory.pages
            inventory_document = {**inventory.to_dict(), "mode": "sitemap"}
        self.registry.register_json(
            "metadata/inventory.json",
            inventory_document,
            metadata={"report_role": "inventory"},
        )

        viewport_config = config["viewports"]
        primary = viewport_config.get("primary", {})
        configured_profiles = config.get("scenarios", {}).get("profiles", {})
        planner = ScenarioPlanner(
            mobile=_viewport(primary.get("mobile"), 390, 844),
            desktop=_viewport(primary.get("desktop"), 1280, 800),
            probe_height=int(viewport_config.get("probe_height", 900)),
            breakpoint_probes=tuple(viewport_config.get("breakpoint_probes", ())),
            profile_scenarios={
                name: tuple(value.get("scenarios", ()))
                for name, value in configured_profiles.items()
            },
            profile_viewports={
                name: tuple(value.get("viewports", ()))
                for name, value in configured_profiles.items()
            },
            breakpoint_route_limit=int(
                config.get("runtime", {}).get("breakpoint_route_limit", 6)
            ),
        )
        audit_plan = planner.plan(
            pages,
            self.options.profile,
            max_representatives=self.options.max_representative_routes,
        )
        cases = list(audit_plan.cases)
        if self.options.max_cases is not None:
            cases = cases[: self.options.max_cases]
        selected_page_ids = {case.page_id for case in cases}
        selected_pages = [
            page_plan.page.to_dict()
            for page_plan in audit_plan.pages
            if page_plan.page.id in selected_page_ids
        ]
        plan = {
            "profile": self.options.profile,
            "pages": selected_pages,
            "cases": [case.to_dict() for case in cases],
            "coverage": {
                **audit_plan.coverage.to_dict(),
                "planned_cases": len(cases),
                "bounded": len(cases) != len(audit_plan.cases),
            },
        }
        self.registry.register_json(
            "metadata/audit-plan.json",
            plan,
            metadata={"report_role": "audit_plan"},
        )
        return plan

    def _load_plan(self) -> dict[str, Any] | None:
        artifacts = [
            item
            for item in self.registry.list_registered(verify=True)
            if item.metadata.get("report_role") == "audit_plan"
        ]
        if not artifacts:
            return None
        return json.loads(self.registry.resolve(artifacts[-1].id).read_text(encoding="utf-8"))

    def _prepare_tasks(self, plan: Mapping[str, Any]) -> None:
        pages = {item["id"]: item for item in plan.get("pages", [])}
        values = []
        for case in plan.get("cases", []):
            values.append(
                (
                    str(case["id"]),
                    "case",
                    {"case": case, "page": pages[case["page_id"]]},
                    100,
                )
            )
        self.state.add_tasks(values)

    async def _execute_pending_cases(self) -> None:
        config = self.config.mutable_copy()
        runtime_options = _runtime_options(config)
        runtime_config = config.get("runtime", {})
        concurrency = max(
            1,
            int(
                os.environ.get(
                    "STORE_PARITY_CONCURRENCY",
                    runtime_config.get("concurrency", 1),
                )
            ),
        )
        retries = max(0, int(runtime_config.get("retries", 0)))
        challenge_backoff_ms = max(
            0,
            int(runtime_config.get("challenge_backoff_ms", 30_000)),
        )
        timeout_backoff_ms = max(
            0,
            int(os.environ.get("STORE_PARITY_TIMEOUT_BACKOFF_MS", "5000")),
        )
        pair_cache_size = max(
            1,
            int(os.environ.get("STORE_PARITY_PAIR_CACHE_SIZE", "2")),
        )
        pair_recycle_cases = max(
            1,
            int(os.environ.get("STORE_PARITY_PAIR_RECYCLE_CASES", "30")),
        )
        runtime = self.runtime_factory(runtime_options)
        fatal_runtime = asyncio.Event()
        attempt_baselines: dict[str, int] = {}

        async def execute_worker() -> None:
            pairs: OrderedDict[BrowserProfile, Any] = OrderedDict()
            pair_uses: dict[BrowserProfile, int] = {}
            try:
                while not fatal_runtime.is_set():
                    task = self.state.claim_next(kind="case")
                    if task is None:
                        break
                    baseline_attempt = attempt_baselines.setdefault(
                        task.id,
                        task.attempts - 1,
                    )
                    run_attempt = task.attempts - baseline_attempt
                    profile = _browser_profile(task.payload["case"])
                    pair = pairs.pop(profile, None)
                    if pair is not None:
                        pairs[profile] = pair
                    try:
                        if pair is None:
                            if len(pairs) >= pair_cache_size:
                                stale_profile, stale_pair = pairs.popitem(last=False)
                                pair_uses.pop(stale_profile, None)
                                await _close_runtime_pair(runtime, stale_pair)
                            pair = await runtime.create_pair(profile)
                            pairs[profile] = pair
                            pair_uses[profile] = 0
                        outcome = await self._execute_case(
                            runtime,
                            task,
                            pair=pair,
                        )
                        pair_uses[profile] = pair_uses.get(profile, 0) + 1
                        self._register_outcome(outcome, task)
                        status = (
                            TaskStatus.FAILED
                            if outcome.result["status"] == CaseStatus.ERROR.value
                            else TaskStatus.SUCCEEDED
                        )
                        if status is TaskStatus.FAILED and run_attempt <= retries:
                            self.state.requeue(
                                task.id,
                                error=outcome.result.get("error"),
                            )
                        else:
                            self.state.finish(
                                task.id,
                                status,
                                error=outcome.result.get("error"),
                            )
                        if pair_uses.get(profile, 0) >= pair_recycle_cases:
                            pairs.pop(profile, None)
                            pair_uses.pop(profile, None)
                            await _close_runtime_pair(runtime, pair)
                    except Exception as error:
                        if pair is not None:
                            try:
                                await _close_runtime_pair(runtime, pair)
                            except Exception:
                                pass
                            pairs.pop(profile, None)
                            pair_uses.pop(profile, None)
                        outcome = self._error_outcome(task, error)
                        self._register_outcome(outcome, task)
                        message = f"{type(error).__name__}: {error}"
                        fatal = any(
                            marker in message
                            for marker in (
                                "Connection closed while reading from the driver",
                                "Browser has been closed",
                                "browser has been closed",
                                "pipe closed by peer",
                            )
                        )
                        if fatal:
                            self.state.requeue(task.id, error=message)
                            fatal_runtime.set()
                            break
                        if run_attempt <= retries:
                            rate_limited = any(
                                marker in message
                                for marker in (
                                    "__cf_chl",
                                    "HTTP 429",
                                    "rendered unknown",
                                )
                            )
                            if rate_limited and challenge_backoff_ms:
                                await asyncio.sleep(
                                    challenge_backoff_ms
                                    * run_attempt
                                    / 1_000
                                )
                            elif "TimeoutError" in message and timeout_backoff_ms:
                                await asyncio.sleep(
                                    timeout_backoff_ms
                                    * run_attempt
                                    / 1_000
                                )
                            self.state.requeue(task.id, error=message)
                        else:
                            self.state.finish(
                                task.id,
                                TaskStatus.FAILED,
                                error=message,
                            )
            finally:
                await asyncio.gather(
                    *(
                        _close_runtime_pair(runtime, pair)
                        for pair in tuple(pairs.values())
                    ),
                    return_exceptions=True,
                )

        async with runtime:
            await asyncio.gather(*(execute_worker() for _ in range(concurrency)))

    async def _execute_case(
        self,
        runtime: Any,
        task: Task,
        *,
        pair: Any | None = None,
    ) -> _CaseOutcome:
        case = dict(task.payload["case"])
        page_value = dict(task.payload["page"])
        started_at = utc_now()
        owns_pair = pair is None
        if pair is None:
            pair = await runtime.create_pair(_browser_profile(case))
        try:
            for session in (pair.live, pair.preview):
                session.telemetry.clear()
                await _install_determinism(
                    session.page,
                    freeze_time=bool(
                        self.config.data.get("dynamic_regions", {}).get("freeze_time", True)
                    ),
                )
            navigations = await asyncio.gather(
                pair.live.navigate(str(case["path"])),
                pair.preview.navigate(str(case["path"])),
            )
            html = await pair.live.page.content()
            enriched = _preserve_page_identity(
                page_value,
                enrich_page_from_rendered_html(_page_from_dict(page_value), html),
                pair.preview.requested_url(str(case["path"])),
            )

            live_behavior, preview_behavior = await _execute_steps_symmetrically(
                pair.live.page,
                pair.preview.page,
                case.get("steps", ()),
            )
            await asyncio.gather(
                pair.live.assert_theme_identity(),
                pair.preview.assert_theme_identity(),
            )
            capture_options = _capture_options(self.config.mutable_copy(), case)
            live_bundle, preview_bundle = await asyncio.gather(
                self.capture_page(
                    pair.live.page,
                    session=pair.live,
                    requested_url=navigations[0].requested_url,
                    options=capture_options,
                ),
                self.capture_page(
                    pair.preview.page,
                    session=pair.preview,
                    requested_url=navigations[1].requested_url,
                    options=capture_options,
                ),
            )
            live_accessibility, live_accessibility_error = await _collect_accessibility(
                pair.live.page,
                self.config.mutable_copy(),
            )
            preview_accessibility, preview_accessibility_error = await _collect_accessibility(
                pair.preview.page,
                self.config.mutable_copy(),
            )
            artifacts = self._register_capture_pair(
                case,
                task.attempts,
                live_bundle,
                preview_bundle,
                live_accessibility,
                preview_accessibility,
                live_behavior,
                preview_behavior,
                live_accessibility_error,
                preview_accessibility_error,
            )
            findings, metrics, diff_artifacts = self._compare(
                case,
                live_bundle,
                preview_bundle,
                live_behavior,
                preview_behavior,
                live_accessibility,
                preview_accessibility,
                live_accessibility_error,
                preview_accessibility_error,
                task.attempts,
            )
            artifacts.extend(diff_artifacts)
            classified = _deduplicate_classified(
                classify_findings(
                    findings,
                    scope=(
                        str(case["page_id"]),
                        str(case["scenario"]),
                        str(case["viewport_name"]),
                    ),
                )
            )
            gate = evaluate_acceptance_gate(classified)
            required_missing = any(
                finding.code in {
                    "capture.required_landmark_missing",
                    "action.required_failed",
                    "accessibility.required_unavailable",
                }
                for finding in findings
            )
            status = (
                CaseStatus.ERROR
                if required_missing
                else CaseStatus.PASSED
                if gate.accepted
                else CaseStatus.FAILED
            )
            evidence_ids = tuple(item.id for item in artifacts)
            issues = tuple(
                _issue_record(case, issue, evidence_ids)
                for issue in classified
            )
            result = {
                "id": case["id"],
                "page_id": case["page_id"],
                "profile": case["profile"],
                "scenario": case["scenario"],
                "feature": case["scenario"],
                "viewport": dict(case["viewport"]),
                "status": status.value,
                "started_at": isoformat(started_at),
                "completed_at": isoformat(utc_now()),
                "artifact_ids": list(evidence_ids),
                "metrics": metrics,
                "error": (
                    "; ".join(gate.reasons)
                    if status is CaseStatus.ERROR
                    else None
                ),
            }
            return _CaseOutcome(
                case=case,
                page=enriched,
                result=result,
                issues=issues,
                classified=classified,
                evidence_ids=evidence_ids,
            )
        finally:
            if owns_pair:
                await _close_runtime_pair(runtime, pair)

    def _register_capture_pair(
        self,
        case: Mapping[str, Any],
        attempt: int,
        live: CaptureBundle,
        preview: CaptureBundle,
        live_accessibility: Sequence[Mapping[str, Any]] | None,
        preview_accessibility: Sequence[Mapping[str, Any]] | None,
        live_behavior: Mapping[str, Any],
        preview_behavior: Mapping[str, Any],
        live_accessibility_error: str | None,
        preview_accessibility_error: str | None,
    ) -> list[Artifact]:
        prefix = f"captures/{case['id']}/attempt-{attempt}"
        artifacts: list[Artifact] = []
        for side, bundle, accessibility, behavior, accessibility_error in (
            (
                "live",
                live,
                live_accessibility,
                live_behavior,
                live_accessibility_error,
            ),
            (
                "preview",
                preview,
                preview_accessibility,
                preview_behavior,
                preview_accessibility_error,
            ),
        ):
            artifacts.append(
                self.registry.register_bytes(
                    f"{prefix}/{side}-viewport.png",
                    bundle.screenshots.viewport,
                    kind=ArtifactKind.SCREENSHOT,
                    media_type="image/png",
                    metadata={"role": side, "capture": "viewport", "case_id": case["id"]},
                )
            )
            artifacts.append(
                self.registry.register_bytes(
                    f"{prefix}/{side}-full-page.png",
                    bundle.screenshots.full_page,
                    kind=ArtifactKind.SCREENSHOT,
                    media_type="image/png",
                    metadata={"role": f"{side}-full-page", "case_id": case["id"]},
                )
            )
            for name, content in bundle.screenshots.components.items():
                artifacts.append(
                    self.registry.register_bytes(
                        f"{prefix}/{side}-component-{_slug(name)}.png",
                        content,
                        kind=ArtifactKind.SCREENSHOT,
                        media_type="image/png",
                        metadata={
                            "role": f"{side}-component",
                            "component": name,
                            "case_id": case["id"],
                        },
                    )
                )
            metadata = bundle.metadata()
            metadata["behavior"] = dict(behavior)
            if accessibility is not None:
                metadata["accessibility"] = list(accessibility)
            if accessibility_error:
                metadata["accessibility_collector_error"] = accessibility_error
            artifacts.append(
                self.registry.register_json(
                    f"{prefix}/{side}-evidence.json",
                    metadata,
                    metadata={"report_role": "capture_evidence", "side": side, "case_id": case["id"]},
                )
            )
        return artifacts

    def _compare(
        self,
        case: Mapping[str, Any],
        live: CaptureBundle,
        preview: CaptureBundle,
        live_behavior: Mapping[str, Any],
        preview_behavior: Mapping[str, Any],
        live_accessibility: Sequence[Mapping[str, Any]] | None,
        preview_accessibility: Sequence[Mapping[str, Any]] | None,
        live_accessibility_error: str | None,
        preview_accessibility_error: str | None,
        attempt: int,
    ) -> tuple[list[DetectorFinding], dict[str, float], list[Artifact]]:
        config = self.config.mutable_copy()
        findings: list[DetectorFinding] = []
        metrics: dict[str, float] = {}
        artifacts: list[Artifact] = []
        visual_config = config.get("tolerances", {}).get("visual", {})
        diff_prefix = f"diffs/{case['id']}/attempt-{attempt}"
        visual_pairs = [
            ("viewport", live.screenshots.viewport, preview.screenshots.viewport, None),
            ("full-page", live.screenshots.full_page, preview.screenshots.full_page, None),
            *(
                (
                    f"component-{_slug(name)}",
                    live.screenshots.components[name],
                    preview.screenshots.components[name],
                    str(name),
                )
                for name in sorted(
                    set(live.screenshots.components)
                    & set(preview.screenshots.components)
                )
            ),
        ]
        for name, baseline_png, candidate_png, selector in visual_pairs:
            visual = compare_images(
                baseline_png,
                candidate_png,
                pixel_threshold=float(visual_config.get("pixel_threshold", 0.10)),
                max_changed_pixel_ratio=float(
                    visual_config.get("max_changed_pixel_ratio", 0.005)
                ),
                max_mean_delta=float(visual_config.get("max_mean_delta", 1.5)),
            )
            findings.extend(visual.findings(selector))
            metrics[f"{name}_changed_pixel_ratio"] = visual.changed_pixel_ratio
            metrics[f"{name}_mean_delta"] = visual.mean_delta
            if name == "viewport":
                metrics["changed_pixel_ratio"] = visual.changed_pixel_ratio
                metrics["mean_delta"] = visual.mean_delta
            artifacts.append(
                self.registry.register_bytes(
                    f"{diff_prefix}/{name}-overlay.png",
                    visual.overlay_png,
                    kind=ArtifactKind.DIFF,
                    media_type="image/png",
                    metadata={
                        "role": "diff",
                        "capture": name,
                        "case_id": case["id"],
                    },
                )
            )
            artifacts.append(
                self.registry.register_bytes(
                    f"{diff_prefix}/{name}-heatmap.png",
                    visual.heatmap_png,
                    kind=ArtifactKind.DIFF,
                    media_type="image/png",
                    metadata={
                        "role": "heatmap",
                        "capture": name,
                        "case_id": case["id"],
                    },
                )
            )

        live_geometry, preview_geometry = _comparable_landmarks(
            live.landmarks, preview.landmarks, "geometry"
        )
        geometry = compare_geometry(
            live_geometry,
            preview_geometry,
            position_tolerance_px=float(
                config.get("tolerances", {}).get("geometry", {}).get("position_px", 2)
            ),
            size_tolerance_px=float(
                config.get("tolerances", {}).get("geometry", {}).get("size_px", 2)
            ),
        )
        findings.extend(geometry.findings)
        live_styles, preview_styles = _comparable_landmarks(
            live.landmarks, preview.landmarks, "style"
        )
        styles = compare_computed_styles(
            live_styles,
            preview_styles,
            color_channel_tolerance=int(
                config.get("tolerances", {}).get("color", {}).get("channel_delta", 3)
            ),
            font_size_tolerance_px=float(
                config.get("tolerances", {}).get("typography", {}).get("font_size_px", 1)
            ),
            line_height_tolerance_px=float(
                config.get("tolerances", {}).get("typography", {}).get("line_height_px", 1)
            ),
        )
        findings.extend(styles.findings)
        findings.extend(compare_dom_semantics(live.dom["nodes"], preview.dom["nodes"]).findings)
        findings.extend(compare_icons(_icons_by_selector(live.icons), _icons_by_selector(preview.icons)).findings)
        findings.extend(compare_behavior_contracts(live_behavior, preview_behavior).findings)
        findings.extend(
            compare_diagnostics(
                live.console_errors,
                preview.console_errors,
                live.failed_first_party_requests,
                preview.failed_first_party_requests,
            ).findings
        )
        if live_accessibility is not None and preview_accessibility is not None:
            accessibility = compare_accessibility_issues(
                live_accessibility,
                preview_accessibility,
            )
            findings.extend(accessibility.findings)
            metrics["new_accessibility_violations"] = float(
                accessibility.new_serious_or_critical
            )
        elif _accessibility_required(config):
            findings.append(
                DetectorFinding(
                    detector="accessibility",
                    code="accessibility.required_unavailable",
                    category="accessibility",
                    message="Required accessibility evidence could not be collected",
                    severity=Severity.BLOCKER,
                    actual={
                        "live_error": live_accessibility_error,
                        "preview_error": preview_accessibility_error,
                    },
                    metadata={"status": IssueStatus.BLOCKED.value},
                )
            )

        for landmark in case.get("landmarks", ()):
            if not landmark.get("required"):
                continue
            name = str(landmark["name"])
            for side, bundle in (("live", live), ("preview", preview)):
                if not bundle.landmarks.get(name, {}).get("matches"):
                    findings.append(
                        DetectorFinding(
                            detector="capture",
                            code="capture.required_landmark_missing",
                            category="layout",
                            message=f"Required landmark {name} is missing on {side}",
                            severity=Severity.BLOCKER,
                            selector=str(landmark["selector"]),
                            metadata={
                                "side": side,
                                "status": IssueStatus.BLOCKED.value,
                                "fingerprint_fields": {"side": side},
                            },
                        )
                    )
        raw_findings = tuple(findings)
        artifacts.append(
            self.registry.register_json(
                f"{diff_prefix}/findings.json",
                {"findings": [finding.to_dict() for finding in raw_findings]},
                metadata={
                    "report_role": "raw_comparison_findings",
                    "case_id": case["id"],
                },
            )
        )
        findings = list(_consolidate_findings(raw_findings))
        metrics["raw_finding_count"] = float(len(raw_findings))
        metrics["finding_count"] = float(len(findings))
        metrics["geometry_elements"] = float(geometry.compared)
        metrics["style_properties"] = float(styles.compared_properties)
        return findings, metrics, artifacts

    def _error_outcome(self, task: Task, error: Exception) -> _CaseOutcome:
        case = dict(task.payload["case"])
        message = f"{type(error).__name__}: {error}"
        finding = DetectorFinding(
            detector="orchestration",
            code="orchestration.case_error",
            category="runtime",
            message=message,
            severity=Severity.BLOCKER,
            metadata={"status": IssueStatus.BLOCKED.value},
        )
        classified = classify_findings(
            (finding,),
            scope=(str(case["page_id"]), str(case["scenario"]), str(case["viewport_name"])),
        )
        result = {
            "id": case["id"],
            "page_id": case["page_id"],
            "profile": case["profile"],
            "scenario": case["scenario"],
            "feature": case["scenario"],
            "viewport": dict(case["viewport"]),
            "status": CaseStatus.ERROR.value,
            "started_at": isoformat(utc_now()),
            "completed_at": isoformat(utc_now()),
            "artifact_ids": [],
            "metrics": {"finding_count": 1.0},
            "error": message,
        }
        return _CaseOutcome(
            case=case,
            page=dict(task.payload["page"]),
            result=result,
            issues=tuple(_issue_record(case, item, ()) for item in classified),
            classified=classified,
            evidence_ids=(),
        )

    def _register_outcome(self, outcome: _CaseOutcome, task: Task) -> Artifact:
        return self.registry.register_json(
            f"metadata/outcomes/{task.id}/attempt-{task.attempts}.json",
            outcome.to_document(),
            metadata={
                "report_role": "case_outcome",
                "case_id": task.id,
                "attempt": task.attempts,
            },
        )

    def _load_latest_outcomes(self) -> tuple[_CaseOutcome, ...]:
        latest: dict[str, Artifact] = {}
        for artifact in self.registry.list_registered(verify=True):
            if artifact.metadata.get("report_role") != "case_outcome":
                continue
            latest[str(artifact.metadata["case_id"])] = artifact
        values: list[_CaseOutcome] = []
        for case_id in sorted(latest):
            document = json.loads(
                self.registry.resolve(latest[case_id].id).read_text(encoding="utf-8")
            )
            classified = tuple(
                ClassifiedIssue(
                    finding=_finding_from_dict(item),
                    fingerprint=str(item["fingerprint"]),
                    status=IssueStatus(str(item["status"])),
                    rationale=item.get("rationale"),
                )
                for item in document.get("classified_issues", ())
            )
            values.append(
                _CaseOutcome(
                    case={},
                    page=document["page"],
                    result=document["case_result"],
                    issues=tuple(document.get("issues", ())),
                    classified=classified,
                    evidence_ids=tuple(document.get("evidence_ids", ())),
                )
            )
        return tuple(values)

    def _aggregate(
        self,
        plan: Mapping[str, Any],
        outcomes: Sequence[_CaseOutcome],
    ) -> tuple[dict[str, Any], tuple[str, ...], bool]:
        pages = {str(item["id"]): dict(item) for item in plan.get("pages", ())}
        evidence_ids: list[str] = []
        issues: list[Mapping[str, Any]] = []
        classified: list[ClassifiedIssue] = []
        for outcome in outcomes:
            pages[str(outcome.page["id"])] = dict(outcome.page)
            evidence_ids.extend(outcome.evidence_ids)
            issues.extend(outcome.issues)
            classified.extend(outcome.classified)
        gate = evaluate_acceptance_gate(classified)
        features = [
            {
                "id": _slug(name),
                "name": name,
                "description": f"Scenario {name}",
            }
            for name in sorted(
                {
                    str(item["scenario"])
                    for item in (outcome.result for outcome in outcomes)
                }
            )
        ]
        document = {
            "pages": list(pages.values()),
            "case_results": [dict(outcome.result) for outcome in outcomes],
            "issues": list(issues),
            "features": features,
            "coverage": [
                {
                    "id": "coverage",
                    **dict(plan.get("coverage", {})),
                    "gate": gate.to_dict(),
                }
            ],
        }
        return document, tuple(dict.fromkeys(evidence_ids)), gate.accepted


def _browser_profile(case: Mapping[str, Any]) -> BrowserProfile:
    return BrowserProfile(
        name=str(case["viewport_name"]),
        width=int(case["viewport"]["width"]),
        height=int(case["viewport"]["height"]),
        mobile=(
            str(case["viewport_kind"]) == "mobile"
            or int(case["viewport"]["width"]) < 768
        ),
    )


async def _close_runtime_pair(runtime: Any, pair: Any) -> None:
    close_pair = getattr(runtime, "close_pair", None)
    if close_pair is not None:
        await close_pair(pair)
    else:
        await pair.close()


async def _execute_steps_symmetrically(
    live_page: Any,
    preview_page: Any,
    steps: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    live_contracts: dict[str, Any] = {}
    preview_contracts: dict[str, Any] = {}
    for index, step in enumerate(steps):
        key = f"{index}:{step.get('action', 'unknown')}"
        live_value, preview_value = await asyncio.gather(
            _execute_step(live_page, step),
            _execute_step(preview_page, step),
        )
        live_contracts[key] = live_value
        preview_contracts[key] = preview_value
        if step.get("required", True):
            errors = [
                f"{side}: {value['error']}"
                for side, value in (("live", live_value), ("preview", preview_value))
                if value.get("status") == "failed"
            ]
            if errors:
                raise ActionError(
                    f"required action {step.get('action')} failed ({'; '.join(errors)})"
                )
    return live_contracts, preview_contracts


async def _execute_step(page: Any, step: Mapping[str, Any]) -> dict[str, Any]:
    action = str(step.get("action", ""))
    target = step.get("target")
    value = step.get("value")
    required = bool(step.get("required", True))
    actions = StoreActions(page)
    try:
        if action == "scroll":
            await page.evaluate("value => window.scrollTo(0, Number(value) || 0)", value)
        elif action == "wait_stable":
            await page.evaluate(
                "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
            )
        elif action in {"open", "open_navigation"} and target in {
            "mobile-menu",
            "navigation",
            None,
        }:
            await actions.open_menu()
        elif action == "open" and target == "desktop-search":
            trigger = await actions._first_visible(  # Reuse the tested conservative selector logic.
                (
                    "button[aria-label*='search' i]",
                    "a[aria-label*='search' i]",
                    "#top-search-toggle",
                    ".header__icon--search",
                    "details-modal.header__search summary",
                )
            )
            await trigger.click()
            await actions._settle()
        elif action == "focus" and target == "search-input":
            locator = await actions._first_visible(
                (
                    "input[type='search']:visible",
                    "input[name='q']:visible",
                    "[role='search'] input:visible",
                )
            )
            await locator.focus()
        elif action == "open_accordion":
            await _open_menu_accordion(actions, str(target))
        elif action == "open_first_accordion":
            if target == "footer":
                await actions.reach_footer()
                await actions.toggle_accordion(
                    selector="footer details summary, [data-footer-accordion] summary",
                    open_state=True,
                )
            else:
                await actions.toggle_accordion(open_state=True)
        elif action == "submit_search":
            await actions.search(str(value or "shoe"), submit=True)
            await page.wait_for_load_state("domcontentloaded")
        elif action == "open_cart":
            await actions.open_cart()
        elif action == "ensure_empty_cart":
            response = await page.evaluate(
                """async () => {
                    const hasItems = Boolean(document.querySelector(
                        'cart-remove-button, #main-cart-items .cart-item, '
                        + '[data-cart-item], form[action="/cart"] [name="updates[]"]'
                    ));
                    if (!hasItems) {
                        return {ok: true, status: 204, cleared: false};
                    }
                    const response = await fetch('/cart/clear.js', {
                        method: 'POST',
                        headers: {'Accept': 'application/json'}
                    });
                    return {ok: response.ok, status: response.status, cleared: true};
                }"""
            )
            if not response.get("ok"):
                raise ActionError(f"cart clear failed with HTTP {response.get('status')}")
            if response.get("cleared"):
                await page.reload(wait_until="domcontentloaded")
        elif action == "advance_time":
            if required:
                raise ActionError("deterministic clock advance is unsupported")
            return {"action": action, "status": "skipped", "reason": "unsupported_optional"}
        else:
            if required:
                raise ActionError(f"unsupported required action: {action}")
            return {"action": action, "status": "skipped", "reason": "unsupported_optional"}
        wait_ms = int(step.get("wait_ms", 0) or 0)
        if wait_ms:
            await page.wait_for_timeout(wait_ms)
        observation = await page.evaluate(
            """() => {
                const query = new URLSearchParams(location.search);
                query.delete('preview_theme_id');
                const normalizedQuery = query.toString();
                return {
                    path: location.pathname + (normalizedQuery ? `?${normalizedQuery}` : ''),
                    scrollY: Math.round(window.scrollY),
                    activeRole: document.activeElement?.getAttribute('role') || null,
                    activeType: document.activeElement?.getAttribute('type') || null
                };
            }"""
        )
        return {"action": action, "status": "applied", "observation": observation}
    except Exception as error:
        return {
            "action": action,
            "status": "failed" if required else "skipped",
            "error": f"{type(error).__name__}: {error}",
        }


async def _open_menu_accordion(actions: StoreActions, target: str) -> None:
    normalized = target.strip().lower()
    contracts = {
        "collection": (
            "MobileMenuCollection",
            ".mobile_menu_top_sapce",
        ),
        "language": (
            "MobileMenuLanguage",
            ".third_main_menu_li_mobile_only",
        ),
        "client services": (
            "MobileMenuClientService",
            ".third_main_menu_li",
        ),
    }
    panel_id, legacy_parent = contracts.get(
        normalized,
        (None, None),
    )
    if panel_id is not None:
        modern = actions.page.locator(
            f"[data-accordion-button][aria-controls='{panel_id}']"
        ).first
        if await modern.is_visible():
            if await modern.get_attribute("aria-expanded") != "true":
                await modern.click()
                await actions._settle()
            return
    if legacy_parent is not None:
        parent = actions.page.locator(legacy_parent).first
        if await parent.is_visible():
            toggle = parent.locator(":scope > .wsmenu-click").first
            if await toggle.is_visible():
                await toggle.click()
                await actions._settle()
                return
            link = parent.locator(":scope > .navtext").first
            if await link.is_visible():
                await link.click()
                await actions._settle()
                return
    await actions.toggle_accordion(text=target, open_state=True)


async def _install_determinism(page: Any, *, freeze_time: bool) -> None:
    if not freeze_time:
        return
    await page.add_init_script(
        """(() => {
            const fixed = 1704067200000;
            const NativeDate = Date;
            class FrozenDate extends NativeDate {
                constructor(...args) { super(...(args.length ? args : [fixed])); }
                static now() { return fixed; }
            }
            window.Date = FrozenDate;
        })();"""
    )


async def _collect_accessibility(
    page: Any,
    config: Mapping[str, Any],
) -> tuple[list[Mapping[str, Any]] | None, str | None]:
    accessibility = config.get("accessibility", {})
    if not isinstance(accessibility, Mapping) or not accessibility.get("enabled", False):
        return None, None
    try:
        from axe_playwright_python.async_playwright import Axe

        result = await Axe().run(page)
        return list(result.response.get("violations", ())), None
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"


def _capture_options(config: Mapping[str, Any], case: Mapping[str, Any]) -> CaptureOptions:
    runtime = config.get("runtime", {})
    pagefly = config.get("pagefly", {}).get("conditional", {})
    landmark_selectors = {
        str(item["name"]): str(item["selector"])
        for item in case.get("landmarks", ())
    }
    readiness_landmarks = tuple(
        str(item["selector"])
        for item in case.get("landmarks", ())
        if item.get("required")
    )
    return CaptureOptions(
        landmark_selectors=landmark_selectors,
        component_selectors=landmark_selectors,
        readiness=ReadinessOptions(
            timeout_ms=int(runtime.get("settle_timeout_ms", 5_000)),
            landmark_selectors=readiness_landmarks,
            pagefly_detect_selectors=(
                tuple(
                    pagefly.get(
                        "detect_selectors",
                        ("[data-pf-type]", ".__pf", "[class*='pagefly']"),
                    )
                )
                if pagefly.get("enabled", True)
                else ()
            ),
            pagefly_wait_for_network_idle=bool(
                pagefly.get("wait_for_network_idle", True)
            ),
            pagefly_extra_stable_frames=int(pagefly.get("extra_stable_frames", 3)),
        ),
    )


def _runtime_options(config: Mapping[str, Any]) -> RuntimeOptions:
    targets = config["targets"]
    preview = targets["preview"]
    runtime = config.get("runtime", {})
    return RuntimeOptions(
        live_base_url=str(targets["live"]["base_url"]),
        preview_base_url=str(preview["base_url"]),
        preview_theme_id=preview["theme_id"],
        preview_query_parameter=str(preview.get("query_parameter", "preview_theme_id")),
        navigation_timeout_ms=int(
            os.environ.get(
                "STORE_PARITY_NAVIGATION_TIMEOUT_MS",
                runtime.get("navigation_timeout_ms", 30_000),
            )
        ),
        action_timeout_ms=int(
            os.environ.get(
                "STORE_PARITY_ACTION_TIMEOUT_MS",
                runtime.get("action_timeout_ms", 10_000),
            )
        ),
        headless=bool(runtime.get("headless", True)),
    )


def _manual_page(base_url: str, path_or_url: str) -> Page:
    url = canonicalize_url(path_or_url, base_url)
    path = urlsplit(url).path
    page_type = classify_page_type(path)
    template = classify_template(path, page_type=page_type)
    signature = feature_signature(None, page_type=page_type, template=template)
    identifier = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    return Page(
        id=f"page-{identifier}",
        url=url,
        path=path,
        page_type=page_type,
        source="manual",
        metadata={
            **signature.to_dict(),
            "canonical_url": url,
            "rendered_signature": False,
        },
    )


def _page_from_dict(value: Mapping[str, Any]) -> Page:
    discovered = str(value.get("discovered_at", isoformat(utc_now())))
    return Page(
        id=str(value["id"]),
        url=str(value["url"]),
        path=str(value["path"]),
        page_type=str(value["page_type"]),
        source=str(value["source"]),
        discovered_at=datetime.fromisoformat(discovered.replace("Z", "+00:00")),
        metadata=dict(value.get("metadata", {})),
    )


def _preserve_page_identity(
    original: Mapping[str, Any],
    enriched: Page,
    preview_url: str,
) -> dict[str, Any]:
    value = enriched.to_dict()
    value["id"] = original["id"]
    value["metadata"] = {**value["metadata"], "preview_url": preview_url}
    return value


def _viewport(value: Any, default_width: int, default_height: int) -> Any:
    from store_parity.models import Viewport

    mapping = value if isinstance(value, Mapping) else {}
    return Viewport(
        int(mapping.get("width", default_width)),
        int(mapping.get("height", default_height)),
    )


def _landmark_values(
    landmarks: Mapping[str, Any],
    key: str,
) -> dict[str, Mapping[str, Any]]:
    values: dict[str, Mapping[str, Any]] = {}
    for name, record in landmarks.items():
        matches = record.get("matches", ()) if isinstance(record, Mapping) else ()
        if matches and isinstance(matches[0], Mapping) and isinstance(matches[0].get(key), Mapping):
            values[str(name)] = dict(matches[0][key])
    return values


def _comparable_landmarks(
    live: Mapping[str, Any],
    preview: Mapping[str, Any],
    key: str,
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    live_values = _landmark_values(live, key)
    preview_values = _landmark_values(preview, key)
    common = set(live_values) & set(preview_values)
    return (
        {name: live_values[name] for name in sorted(common)},
        {name: preview_values[name] for name in sorted(common)},
    )


def _icons_by_selector(values: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    counts: dict[str, int] = {}
    for item in values:
        selector = str(item.get("selector", "icon"))
        counts[selector] = counts.get(selector, 0) + 1
        result[f"{selector}:{counts[selector]}"] = dict(item)
    return result


def _finding_from_dict(value: Mapping[str, Any]) -> DetectorFinding:
    return DetectorFinding(
        detector=str(value["detector"]),
        code=str(value["code"]),
        category=str(value["category"]),
        message=str(value["message"]),
        severity=Severity(str(value["severity"])),
        confidence=float(value.get("confidence", 1.0)),
        selector=value.get("selector"),
        expected=value.get("expected"),
        actual=value.get("actual"),
        metadata=dict(value.get("metadata", {})),
        exact_identity=bool(value.get("exact_identity", False)),
    )


def _issue_record(
    case: Mapping[str, Any],
    issue: ClassifiedIssue,
    artifact_ids: Sequence[str],
) -> dict[str, Any]:
    finding = issue.finding
    return {
        "id": f"issue-{issue.fingerprint[:24]}",
        "case_result_id": case["id"],
        "page_id": case["page_id"],
        "feature": case["scenario"],
        "category": finding.category,
        "severity": finding.severity.value,
        "status": issue.status.value,
        "title": finding.message,
        "description": (
            f"{finding.code}. Expected: {finding.expected!r}; actual: {finding.actual!r}"
        ),
        "selector": finding.selector,
        "artifact_ids": list(artifact_ids),
        "created_at": isoformat(utc_now()),
        "fingerprint": issue.fingerprint,
    }


def _case_counts(outcomes: Sequence[_CaseOutcome]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for outcome in outcomes:
        status = str(outcome.result["status"])
        counts[status] = counts.get(status, 0) + 1
    return counts


def _validate_report_records(document: Mapping[str, Any]) -> None:
    schemas = Path(__file__).resolve().parents[2] / "schemas"
    collections = (
        ("pages", "page.schema.json"),
        ("case_results", "case-result.schema.json"),
        ("issues", "issue.schema.json"),
    )
    for collection, schema_name in collections:
        validator = Draft202012Validator(
            json.loads((schemas / schema_name).read_text(encoding="utf-8")),
            format_checker=FormatChecker(),
        )
        for record in document.get(collection, ()):
            validator.validate(record)


def _consolidate_findings(
    findings: Sequence[DetectorFinding],
    *,
    threshold: int = 20,
) -> tuple[DetectorFinding, ...]:
    grouped: dict[tuple[str, str, str, Severity], list[DetectorFinding]] = defaultdict(list)
    for finding in findings:
        grouped[
            (
                finding.detector,
                finding.code,
                finding.category,
                finding.severity,
            )
        ].append(finding)

    consolidated: list[DetectorFinding] = []
    for key in sorted(grouped, key=lambda item: tuple(str(value) for value in item)):
        values = grouped[key]
        if len(values) <= threshold:
            consolidated.extend(values)
            continue
        sample_selectors = tuple(
            dict.fromkeys(
                finding.selector
                for finding in values
                if finding.selector is not None
            )
        )[:10]
        first = values[0]
        consolidated.append(
            DetectorFinding(
                detector=first.detector,
                code=first.code,
                category=first.category,
                message=f"{len(values)} occurrences: {first.message}",
                severity=first.severity,
                confidence=min(item.confidence for item in values),
                expected=first.expected,
                actual={
                    "occurrences": len(values),
                    "sample_selectors": list(sample_selectors),
                },
                metadata={
                    **dict(first.metadata),
                    "occurrences": len(values),
                    "sample_selectors": list(sample_selectors),
                },
                exact_identity=any(item.exact_identity for item in values),
            )
        )
    return tuple(consolidated)


def _deduplicate_classified(
    issues: Sequence[ClassifiedIssue],
) -> tuple[ClassifiedIssue, ...]:
    unique: dict[str, ClassifiedIssue] = {}
    for issue in issues:
        unique.setdefault(issue.fingerprint, issue)
    return tuple(unique.values())


def _accessibility_required(config: Mapping[str, Any]) -> bool:
    value = config.get("accessibility", {})
    return bool(isinstance(value, Mapping) and value.get("enabled") and value.get("required"))


def _slug(value: Any) -> str:
    text = "".join(character.lower() if character.isalnum() else "-" for character in str(value))
    return "-".join(part for part in text.split("-") if part) or "item"


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "store-parity/0.1 (+parity audit)"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")

