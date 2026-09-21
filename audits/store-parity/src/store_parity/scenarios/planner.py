from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from store_parity.inventory import (
    greedy_set_cover,
    metadata_signature,
    profile_coverage,
    select_profile_routes,
)
from store_parity.models import Page, Viewport

from .definitions import (
    SCENARIO_DEFINITIONS,
    Landmark,
    ScenarioDefinition,
    ScenarioStep,
)


BREAKPOINT_TARGETS = (750, 767, 990, 991, 992, 1024)
BREAKPOINT_PROBES = tuple(
    sorted({width + offset for width in BREAKPOINT_TARGETS for offset in (-1, 0, 1)})
)

PRIMARY_VIEWPORTS: Mapping[str, Viewport] = {
    "mobile": Viewport(390, 844),
    "desktop": Viewport(1280, 800),
}

PROFILE_SCENARIOS: Mapping[str, tuple[str, ...]] = {
    "mobile-p0": (
        "baseline",
        "announcement-header-scroll",
        "mobile-menu-closed",
        "mobile-menu-open",
        "mobile-menu-collection-open",
        "mobile-menu-language-open",
        "mobile-menu-client-services-open",
        "newsletter-timed",
        "footer-accordion",
        "collection-state",
        "product-state",
    ),
    "smoke": (
        "baseline",
        "announcement-header-scroll",
        "mobile-menu-closed",
        "mobile-menu-open",
        "desktop-search",
        "cart-empty",
        "collection-state",
        "search-state",
        "product-state",
        "cart-state",
        "page-state",
    ),
    "full": tuple(SCENARIO_DEFINITIONS),
}

GLOBAL_SCENARIOS = frozenset(
    {
        "announcement-header-scroll",
        "mobile-menu-closed",
        "mobile-menu-open",
        "mobile-menu-collection-open",
        "mobile-menu-language-open",
        "mobile-menu-client-services-open",
        "desktop-search",
        "newsletter-timed",
        "footer-accordion",
    }
)

TYPED_DEFAULT_SCENARIOS: Mapping[str, str] = {
    "collection": "collection-state",
    "product": "product-state",
    "page": "page-state",
    "blog": "page-state",
    "article": "page-state",
    "search": "search-state",
    "cart": "cart-state",
    "other": "page-state",
}


@dataclass(frozen=True, slots=True)
class CasePlan:
    id: str
    page_id: str
    path: str
    page_type: str
    profile: str
    scenario: str
    viewport_name: str
    viewport_kind: str
    viewport: Viewport
    required: bool
    landmarks: tuple[Landmark, ...]
    steps: tuple[ScenarioStep, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "page_id": self.page_id,
            "path": self.path,
            "page_type": self.page_type,
            "profile": self.profile,
            "scenario": self.scenario,
            "viewport_name": self.viewport_name,
            "viewport_kind": self.viewport_kind,
            "viewport": self.viewport.to_dict(),
            "required": self.required,
            "landmarks": [landmark.to_dict() for landmark in self.landmarks],
            "steps": [step.to_dict() for step in self.steps],
        }


@dataclass(frozen=True, slots=True)
class PagePlan:
    page: Page
    cases: tuple[CasePlan, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "page": self.page.to_dict(),
            "cases": [case.to_dict() for case in self.cases],
        }


@dataclass(frozen=True, slots=True)
class CoverageSummary:
    inventory_routes: int
    selected_routes: int
    total_cases: int
    required_cases: int
    optional_cases: int
    routes_by_type: Mapping[str, int]
    cases_by_scenario: Mapping[str, int]
    covered_features: tuple[str, ...]
    uncovered_features: tuple[str, ...]
    covered_tokens: tuple[str, ...]
    uncovered_tokens: tuple[str, ...]
    breakpoint_probes: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "inventory_routes": self.inventory_routes,
            "selected_routes": self.selected_routes,
            "total_cases": self.total_cases,
            "required_cases": self.required_cases,
            "optional_cases": self.optional_cases,
            "routes_by_type": dict(self.routes_by_type),
            "cases_by_scenario": dict(self.cases_by_scenario),
            "covered_features": list(self.covered_features),
            "uncovered_features": list(self.uncovered_features),
            "covered_tokens": list(self.covered_tokens),
            "uncovered_tokens": list(self.uncovered_tokens),
            "breakpoint_probes": list(self.breakpoint_probes),
        }


@dataclass(frozen=True, slots=True)
class AuditPlan:
    profile: str
    pages: tuple[PagePlan, ...]
    coverage: CoverageSummary

    @property
    def cases(self) -> tuple[CasePlan, ...]:
        return tuple(case for page in self.pages for case in page.cases)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "pages": [page.to_dict() for page in self.pages],
            "coverage": self.coverage.to_dict(),
        }


class ScenarioPlanner:
    def __init__(
        self,
        *,
        mobile: Viewport = PRIMARY_VIEWPORTS["mobile"],
        desktop: Viewport = PRIMARY_VIEWPORTS["desktop"],
        probe_height: int = 900,
        breakpoint_probes: Sequence[int] = BREAKPOINT_PROBES,
        profile_scenarios: Mapping[str, Sequence[str]] | None = None,
        profile_viewports: Mapping[str, Sequence[str]] | None = None,
        breakpoint_route_limit: int = 6,
    ) -> None:
        if probe_height <= 0:
            raise ValueError("probe_height must be positive")
        if breakpoint_route_limit <= 0:
            raise ValueError("breakpoint_route_limit must be positive")
        probes = tuple(sorted(set(int(width) for width in breakpoint_probes)))
        if any(width <= 0 for width in probes):
            raise ValueError("breakpoint probes must be positive")
        self.mobile = mobile
        self.desktop = desktop
        self.probe_height = probe_height
        self.breakpoint_probes = probes
        self.breakpoint_route_limit = breakpoint_route_limit
        self.profile_scenarios = {
            name: tuple(values)
            for name, values in (profile_scenarios or PROFILE_SCENARIOS).items()
        }
        self.profile_viewports = {
            name: tuple(values)
            for name, values in (
                profile_viewports
                or {
                    "mobile-p0": ("mobile",),
                    "smoke": ("mobile", "desktop"),
                    "full": ("mobile", "desktop", "breakpoint_probes"),
                }
            ).items()
        }
        for profile in PROFILE_SCENARIOS:
            if profile not in self.profile_scenarios:
                raise ValueError(f"missing scenario profile: {profile}")
            if profile not in self.profile_viewports:
                raise ValueError(f"missing viewport profile: {profile}")
            unknown = set(self.profile_scenarios[profile]) - set(SCENARIO_DEFINITIONS)
            if unknown:
                raise ValueError(
                    f"unknown scenarios for {profile}: {', '.join(sorted(unknown))}"
                )
            invalid_viewports = set(self.profile_viewports[profile]) - {
                "mobile",
                "desktop",
                "breakpoint_probes",
            }
            if invalid_viewports:
                raise ValueError(
                    f"unknown viewports for {profile}: "
                    f"{', '.join(sorted(invalid_viewports))}"
                )

    def plan(
        self,
        pages: Iterable[Page],
        profile: str,
        *,
        max_representatives: int | None = None,
    ) -> AuditPlan:
        inventory = tuple(pages)
        if profile not in self.profile_scenarios:
            raise ValueError(f"unknown scenario profile: {profile}")
        selected = select_profile_routes(
            inventory,
            profile,
            max_representatives=max_representatives,
        )
        viewports = self._profile_viewports(profile)
        global_page_id = next(
            (page.id for page in selected if page.path == "/"),
            selected[0].id if selected else None,
        )
        breakpoint_page_ids = {
            page.id
            for page in greedy_set_cover(
                selected,
                limit=min(self.breakpoint_route_limit, len(selected)),
            )
        }
        page_plans: list[PagePlan] = []
        all_cases: list[CasePlan] = []
        for page in selected:
            page_cases: list[CasePlan] = []
            for scenario_name in self.profile_scenarios[profile]:
                definition = SCENARIO_DEFINITIONS[scenario_name]
                if scenario_name in GLOBAL_SCENARIOS and page.id != global_page_id:
                    continue
                for viewport_name, viewport_kind, viewport in viewports:
                    if (
                        profile == "full"
                        and scenario_name == "baseline"
                        and viewport_kind != "breakpoint"
                        and TYPED_DEFAULT_SCENARIOS.get(page.page_type)
                        in self.profile_scenarios[profile]
                    ):
                        # The typed default scenario captures the same settled
                        # state with stricter page-specific landmarks. Keep
                        # baseline only for home and representative breakpoint
                        # probes to avoid duplicate full-page evidence.
                        continue
                    if (
                        viewport_kind == "breakpoint"
                        and page.id not in breakpoint_page_ids
                    ):
                        continue
                    if not self._should_plan(
                        definition,
                        page,
                        viewport_name,
                        viewport_kind,
                    ):
                        continue
                    case = _make_case(
                        page,
                        profile,
                        definition,
                        viewport_name,
                        viewport_kind,
                        viewport,
                    )
                    page_cases.append(case)
                    all_cases.append(case)
            page_plans.append(PagePlan(page=page, cases=tuple(page_cases)))

        coverage = _coverage_summary(
            inventory,
            selected,
            all_cases,
            breakpoint_probes=(
                self.breakpoint_probes
                if "breakpoint_probes" in self.profile_viewports[profile]
                else ()
            ),
        )
        return AuditPlan(profile=profile, pages=tuple(page_plans), coverage=coverage)

    def _profile_viewports(
        self,
        profile: str,
    ) -> tuple[tuple[str, str, Viewport], ...]:
        configured = self.profile_viewports[profile]
        values: list[tuple[str, str, Viewport]] = []
        if "mobile" in configured:
            values.append(("mobile", "mobile", self.mobile))
        if "desktop" in configured:
            values.append(("desktop", "desktop", self.desktop))
        if "breakpoint_probes" in configured:
            values.extend(
                (
                    f"breakpoint-{width}",
                    "breakpoint",
                    Viewport(width, self.probe_height),
                )
                for width in self.breakpoint_probes
            )
        return tuple(values)

    @staticmethod
    def _should_plan(
        definition: ScenarioDefinition,
        page: Page,
        viewport_name: str,
        viewport_kind: str,
    ) -> bool:
        if not definition.applies_to(page.page_type, viewport_kind):
            return False
        if viewport_kind == "breakpoint":
            return definition.name == "baseline"
        if definition.name.startswith("mobile-menu") and viewport_kind != "mobile":
            return False
        if definition.name == "footer-accordion" and viewport_kind != "mobile":
            return False
        if definition.name == "desktop-search" and viewport_kind != "desktop":
            return False
        return True


def plan_scenarios(
    pages: Iterable[Page],
    profile: str,
    **planner_options: Any,
) -> AuditPlan:
    return ScenarioPlanner(**planner_options).plan(pages, profile)


def _make_case(
    page: Page,
    profile: str,
    definition: ScenarioDefinition,
    viewport_name: str,
    viewport_kind: str,
    viewport: Viewport,
) -> CasePlan:
    identity = "\x00".join((page.id, profile, definition.name, viewport_name))
    case_id = f"case-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]}"
    return CasePlan(
        id=case_id,
        page_id=page.id,
        path=page.path,
        page_type=page.page_type,
        profile=profile,
        scenario=definition.name,
        viewport_name=viewport_name,
        viewport_kind=viewport_kind,
        viewport=viewport,
        required=definition.required,
        landmarks=definition.landmarks,
        steps=definition.steps,
    )


def _coverage_summary(
    inventory: Sequence[Page],
    selected: Sequence[Page],
    cases: Sequence[CasePlan],
    *,
    breakpoint_probes: tuple[int, ...],
) -> CoverageSummary:
    route_coverage = profile_coverage(selected, inventory)
    available_features = {
        feature
        for page in inventory
        for feature in metadata_signature(page.metadata).features
    }
    scenarios = {case.scenario for case in cases}
    exercised_features = {
        definition.feature
        for name, definition in SCENARIO_DEFINITIONS.items()
        if name in scenarios and definition.feature
    }
    covered_features = available_features & exercised_features
    route_counts = Counter(page.page_type for page in selected)
    scenario_counts = Counter(case.scenario for case in cases)
    return CoverageSummary(
        inventory_routes=len(inventory),
        selected_routes=len(selected),
        total_cases=len(cases),
        required_cases=sum(case.required for case in cases),
        optional_cases=sum(not case.required for case in cases),
        routes_by_type=dict(sorted(route_counts.items())),
        cases_by_scenario=dict(sorted(scenario_counts.items())),
        covered_features=tuple(sorted(covered_features)),
        uncovered_features=tuple(sorted(available_features - covered_features)),
        covered_tokens=tuple(route_coverage["covered_tokens"]),
        uncovered_tokens=tuple(route_coverage["uncovered_tokens"]),
        breakpoint_probes=breakpoint_probes,
    )
