from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from store_parity.issues import DetectorFinding, Severity


SEMANTIC_ATTRIBUTES = {
    "action",
    "alt",
    "aria-checked",
    "aria-current",
    "aria-disabled",
    "aria-expanded",
    "aria-haspopup",
    "aria-hidden",
    "aria-label",
    "aria-labelledby",
    "aria-live",
    "checked",
    "disabled",
    "for",
    "href",
    "label",
    "method",
    "name",
    "placeholder",
    "role",
    "selected",
    "src",
    "target",
    "title",
    "type",
    "value",
}
_IGNORED_TAGS = {"script", "style", "template", "noscript"}
_VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
_VOLATILE_QUERY = {"preview_theme_id", "_pos", "_sid", "_ss", "timestamp"}


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _normalize_url(value: str) -> str:
    parsed = urlsplit(value)
    query = urlencode(
        sorted(
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            if key not in _VOLATILE_QUERY
        )
    )
    return urlunsplit(("", "", parsed.path, query, parsed.fragment))


def _normalize_attributes(attributes: Mapping[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for raw_name, raw_value in sorted(attributes.items()):
        name = str(raw_name).lower()
        if name not in SEMANTIC_ATTRIBUTES and not name.startswith("aria-"):
            continue
        value = "" if raw_value is None else _normalize_text(raw_value)
        if name in {"href", "src", "action"}:
            value = _normalize_url(value)
        normalized[name] = value
    return normalized


class _SemanticHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.nodes: list[dict[str, Any]] = []
        self._stack: list[int | None] = []
        self._ignored_depth = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag in _IGNORED_TAGS:
            self._ignored_depth += 1
            self._stack.append(None)
            return
        if self._ignored_depth:
            self._stack.append(None)
            return
        index = len(self.nodes)
        self.nodes.append(
            {
                "selector": f"dom[{index}]",
                "tag": tag.lower(),
                "text": "",
                "attributes": _normalize_attributes(dict(attrs)),
            }
        )
        if tag not in _VOID_TAGS:
            self._stack.append(index)

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        stack_size = len(self._stack)
        self.handle_starttag(tag, attrs)
        if len(self._stack) > stack_size:
            self._stack.pop()

    def handle_endtag(self, tag: str) -> None:
        if not self._stack:
            return
        marker = self._stack.pop()
        if tag in _IGNORED_TAGS and marker is None and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        text = _normalize_text(data)
        if not text:
            return
        for index in reversed(self._stack):
            if index is not None:
                current = self.nodes[index]["text"]
                self.nodes[index]["text"] = _normalize_text(f"{current} {text}")
                break


def _node_from_mapping(
    node: Mapping[str, Any],
    *,
    default_selector: str,
) -> dict[str, Any]:
    attributes = node.get("attributes", node.get("attrs", {}))
    if not isinstance(attributes, Mapping):
        attributes = {}
    return {
        "selector": str(node.get("selector", node.get("path", default_selector))),
        "tag": str(node.get("tag", node.get("tagName", ""))).lower(),
        "text": _normalize_text(
            node.get("text", node.get("textContent", node.get("name", "")))
        ),
        "attributes": _normalize_attributes(attributes),
    }


def semantic_snapshot(
    value: str | Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    if isinstance(value, str):
        parser = _SemanticHTMLParser()
        parser.feed(value)
        parser.close()
        return tuple(parser.nodes)
    if isinstance(value, Mapping):
        if any(key in value for key in ("tag", "tagName", "attributes", "attrs")):
            return (_node_from_mapping(value, default_selector="dom[0]"),)
        return tuple(
            _node_from_mapping(node, default_selector=str(selector))
            for selector, node in sorted(value.items(), key=lambda pair: str(pair[0]))
            if isinstance(node, Mapping)
        )
    return tuple(
        _node_from_mapping(node, default_selector=f"dom[{index}]")
        for index, node in enumerate(value)
    )


@dataclass(frozen=True, slots=True)
class DOMComparison:
    passed: bool
    findings: tuple[DetectorFinding, ...]
    compared_nodes: int


def compare_dom_semantics(
    baseline: str | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    candidate: str | Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> DOMComparison:
    expected_nodes = {
        node["selector"]: node for node in semantic_snapshot(baseline)
    }
    actual_nodes = {
        node["selector"]: node for node in semantic_snapshot(candidate)
    }
    findings: list[DetectorFinding] = []
    for selector in sorted(set(expected_nodes) | set(actual_nodes)):
        expected = expected_nodes.get(selector)
        actual = actual_nodes.get(selector)
        if expected == actual:
            continue
        if expected is None or actual is None:
            code = "dom.semantic_node_missing"
            message = f"Semantic DOM node presence differs for {selector}"
        else:
            code = "dom.semantic_mismatch"
            message = f"Semantic DOM content differs for {selector}"
        findings.append(
            DetectorFinding(
                detector="dom-semantic",
                code=code,
                category="content",
                message=message,
                severity=Severity.MAJOR,
                selector=selector,
                expected=expected,
                actual=actual,
                metadata={"identity_scope": "semantic"},
                exact_identity=True,
            )
        )
    return DOMComparison(
        passed=not findings,
        findings=tuple(findings),
        compared_nodes=len(set(expected_nodes) | set(actual_nodes)),
    )


compare_dom = compare_dom_semantics
