from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from store_parity.models import Page


PAGEFLY_CONDITIONAL = "conditional"
PAGEFLY_APPLICABLE = "applicable"
PAGEFLY_NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class FeatureSignature:
    """Stable, JSON-safe description of features visible in rendered markup."""

    template: str
    features: tuple[str, ...] = ()
    pagefly: str = PAGEFLY_NOT_APPLICABLE

    def tokens(self) -> frozenset[str]:
        values = {f"template:{self.template}", f"pagefly:{self.pagefly}"}
        values.update(f"feature:{feature}" for feature in self.features)
        return frozenset(values)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template": self.template,
            "features": list(self.features),
            "pagefly": self.pagefly,
        }


@dataclass(frozen=True, slots=True)
class InventoryResult:
    pages: tuple[Page, ...]
    sitemap_urls: tuple[str, ...] = ()
    truncated: bool = False
    errors: tuple[str, ...] = ()

    def by_path(self) -> dict[str, Page]:
        return {page.path: page for page in self.pages}

    def to_dict(self) -> dict[str, Any]:
        return {
            "pages": [page.to_dict() for page in self.pages],
            "sitemap_urls": list(self.sitemap_urls),
            "truncated": self.truncated,
            "errors": list(self.errors),
        }


def metadata_signature(metadata: Mapping[str, Any]) -> FeatureSignature:
    raw_features = metadata.get("features", ())
    features: Iterable[str]
    if isinstance(raw_features, (list, tuple, set, frozenset)):
        features = (str(item) for item in raw_features)
    else:
        features = ()
    return FeatureSignature(
        template=str(metadata.get("template", "unknown")),
        features=tuple(sorted(set(features))),
        pagefly=str(metadata.get("pagefly", PAGEFLY_NOT_APPLICABLE)),
    )


def page_to_dict(page: Page) -> dict[str, Any]:
    """Explicit helper used by plan serializers and fixture consumers."""

    return page.to_dict()
