from __future__ import annotations

from store_parity.compare import (
    compare_accessibility_issues,
    compare_behavior_contracts,
    compare_computed_styles,
    compare_diagnostics,
    compare_dom_semantics,
    compare_geometry,
    compare_icons,
    normalize_color,
)


def test_geometry_honors_position_and_size_tolerances() -> None:
    baseline = {"#buy": {"x": 10, "y": 20, "width": 100, "height": 40}}
    inside = {"#buy": {"x": 12, "y": 18, "width": 102, "height": 38}}
    outside = {"#buy": {"x": 13, "y": 20, "width": 100, "height": 40}}

    assert compare_geometry(baseline, inside).passed
    comparison = compare_geometry(baseline, outside)
    assert not comparison.passed
    assert comparison.findings[0].metadata["deltas"] == {"x": 3.0}


def test_computed_style_normalization_and_tolerances() -> None:
    baseline = {
        "button": {
            "color": "#ff0000",
            "font-family": '"Helvetica Neue", Arial',
            "font-size": "16.0px",
            "display": "BLOCK",
        }
    }
    candidate = {
        "button": {
            "color": "rgb(254, 1, 0)",
            "font-family": "helvetica neue,arial",
            "font-size": "16.8px",
            "display": "block",
        }
    }

    assert normalize_color("#fff") == "rgba(255,255,255,255)"
    assert compare_computed_styles(baseline, candidate).passed


def test_semantic_icon_and_behavior_differences_are_exact() -> None:
    dom = compare_dom_semantics(
        {"button": {"tag": "button", "text": "Buy", "attrs": {"type": "button"}}},
        {"button": {"tag": "button", "text": "Sold out", "attrs": {"type": "button"}}},
    )
    assert not dom.passed
    assert dom.findings[0].exact_identity

    icons = compare_icons(
        {"cart": '<svg viewBox="0 0 10 10"><path d="M0,0 L1,1"/></svg>'},
        {"cart": '<svg viewBox="0 0 10 10"><path d="M0,0 L2,2"/></svg>'},
    )
    assert not icons.passed
    assert icons.findings[0].metadata["identity_scope"] == "theme"

    behavior = compare_behavior_contracts(
        {"add-to-cart": {"result": "drawer-open"}},
        {"add-to-cart": {"result": "redirect"}},
    )
    assert not behavior.passed
    assert behavior.findings[0].category == "interaction"


def test_dom_snapshot_uses_collector_paths_as_stable_identity() -> None:
    comparison = compare_dom_semantics(
        [{"path": "main > button", "tag": "button", "text": "Buy", "attributes": {}}],
        [
            {
                "path": "main > button",
                "tag": "button",
                "text": "Sold out",
                "attributes": {},
            }
        ],
    )

    assert comparison.compared_nodes == 1
    assert comparison.findings[0].selector == "main > button"


def test_accessibility_and_runtime_diagnostics_report_only_new_errors() -> None:
    baseline_a11y = [
        {
            "id": "color-contrast",
            "impact": "serious",
            "nodes": [{"target": [".legacy"]}],
        }
    ]
    candidate_a11y = [
        *baseline_a11y,
        {
            "id": "button-name",
            "impact": "critical",
            "nodes": [{"target": ["#checkout"]}],
        },
        {
            "id": "landmark-one-main",
            "impact": "moderate",
            "nodes": [{"target": ["body"]}],
        },
    ]
    accessibility = compare_accessibility_issues(
        baseline_a11y, candidate_a11y
    )
    assert accessibility.new_serious_or_critical == 1
    assert accessibility.findings[0].selector == "#checkout"

    volatile_ids = compare_accessibility_issues(
        [
            {
                "id": "label",
                "impact": "critical",
                "nodes": [
                    {
                        "target": [
                            "#compact-d1af22ba-382a-4c29-97cb-0c9668f92f3b"
                        ]
                    }
                ],
            }
        ],
        [
            {
                "id": "label",
                "impact": "critical",
                "nodes": [
                    {
                        "target": [
                            "#compact-e4a772a3-677c-467b-aa60-e48507a0b014"
                        ]
                    }
                ],
            }
        ],
    )
    assert volatile_ids.passed

    diagnostics = compare_diagnostics(
        baseline_console=[{"type": "error", "text": "legacy error"}],
        candidate_console=[
            {"type": "error", "text": "legacy error"},
            {"type": "error", "text": "new error"},
        ],
        candidate_network=[
            {"method": "GET", "url": "https://shop.test/cart.js", "status": 500}
        ],
    )
    assert not diagnostics.passed
    assert diagnostics.console_errors == 1
    assert diagnostics.network_errors == 1
