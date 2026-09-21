"""Deterministic store-parity comparison detectors."""

from store_parity.compare.accessibility import (
    AccessibilityComparison,
    compare_accessibility_issues,
    diff_accessibility,
)
from store_parity.compare.behavior import (
    BehaviorComparison,
    compare_behavior_contracts,
    compare_behaviors,
)
from store_parity.compare.diagnostics import (
    DiagnosticComparison,
    compare_diagnostics,
    diagnose_console_and_network,
)
from store_parity.compare.dom import (
    DOMComparison,
    compare_dom,
    compare_dom_semantics,
    semantic_snapshot,
)
from store_parity.compare.geometry import (
    GeometryComparison,
    Rect,
    compare_geometry,
    compare_layout_geometry,
)
from store_parity.compare.icons import (
    IconComparison,
    compare_icon_identity,
    compare_icons,
    normalize_icon,
)
from store_parity.compare.styles import (
    StyleComparison,
    compare_computed_styles,
    compare_styles,
    is_visible,
    normalize_color,
    normalize_computed_style,
    normalize_numbers,
    normalize_style_value,
)
from store_parity.compare.visual import (
    DynamicMask,
    VisualDiffResult,
    compare_images,
    compare_pngs,
)

__all__ = [
    "AccessibilityComparison",
    "BehaviorComparison",
    "DOMComparison",
    "DiagnosticComparison",
    "DynamicMask",
    "GeometryComparison",
    "IconComparison",
    "Rect",
    "StyleComparison",
    "VisualDiffResult",
    "compare_accessibility_issues",
    "compare_behavior_contracts",
    "compare_behaviors",
    "compare_computed_styles",
    "compare_diagnostics",
    "compare_dom",
    "compare_dom_semantics",
    "compare_geometry",
    "compare_icon_identity",
    "compare_icons",
    "compare_images",
    "compare_layout_geometry",
    "compare_pngs",
    "compare_styles",
    "diagnose_console_and_network",
    "diff_accessibility",
    "is_visible",
    "normalize_color",
    "normalize_computed_style",
    "normalize_icon",
    "normalize_numbers",
    "normalize_style_value",
    "semantic_snapshot",
]
