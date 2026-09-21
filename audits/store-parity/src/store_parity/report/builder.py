from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import unquote, urlsplit

from store_parity.artifacts import ArtifactError, ArtifactRegistry
from store_parity.layout import RunLayout
from store_parity.models import Artifact, RunStatus


class ReportBuildError(RuntimeError):
    """Raised when trusted report inputs cannot produce a valid static report."""


@dataclass(frozen=True, slots=True)
class ReportResult:
    output_dir: Path
    index_path: Path
    generated_files: tuple[Path, ...]
    source_artifact_ids: tuple[str, ...]
    incomplete: bool


def _text(value: Any, default: str = "") -> str:
    return default if value is None else str(value)


def _slug(value: Any) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", _text(value).lower()).strip("-")
    return normalized or "elemento"


def _unique_slugs(records: Sequence[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    used: set[str] = set()
    for index, record in enumerate(records):
        identifier = _text(record.get("id"), f"item-{index + 1}")
        candidate = _slug(identifier)
        suffix = 2
        while candidate in used:
            candidate = f"{_slug(identifier)}-{suffix}"
            suffix += 1
        used.add(candidate)
        result[identifier] = candidate
    return result


def _as_records(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _json_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")


class ReportBuilder:
    """Build a navigable report from an explicit manifest and its registry entries.

    No directory enumeration is used for input discovery. Only IDs in
    ``manifest["artifact_ids"]`` are resolved, hash-checked, and consumed.
    """

    _COLLECTION_KEYS = {
        "pages": "pages",
        "routes": "pages",
        "case_results": "cases",
        "cases": "cases",
        "issues": "issues",
        "features": "features",
        "coverage": "coverage",
    }
    _ROLE_KEYS = (
        "report_role",
        "entity_type",
        "data_type",
        "content_type",
        "collection",
    )

    def __init__(
        self,
        registry: ArtifactRegistry,
        *,
        manifest: Mapping[str, Any] | None = None,
        output_dir: str | Path | None = None,
        allow_incomplete: bool = False,
    ) -> None:
        self.registry = registry
        self.layout = registry.layout
        self.manifest = dict(manifest) if manifest is not None else self._read_manifest()
        self.output_dir = (
            Path(output_dir).expanduser().resolve()
            if output_dir is not None
            else (self.layout.root / "report").resolve()
        )
        self.allow_incomplete = allow_incomplete
        self._artifacts: dict[str, Artifact] = {}
        self._artifact_paths: dict[str, Path] = {}

    def build(self) -> ReportResult:
        incomplete = self._validate_manifest_state()
        artifacts = self._resolve_manifest_artifacts()
        data = self._load_registered_data(artifacts)
        self._normalize(data)

        if self.output_dir == self.layout.root or self.layout.root in self.output_dir.parents:
            pass
        elif self.output_dir in self.layout.root.parents:
            raise ReportBuildError("report output may not contain the immutable run directory")

        staging = self.output_dir.with_name(f".{self.output_dir.name}.tmp")
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        try:
            generated = self._render(staging, data, incomplete)
            validate_report_links(staging, allowed_root=self.layout.root)
            if self.output_dir.exists():
                shutil.rmtree(self.output_dir)
            os.replace(staging, self.output_dir)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise

        final_files = tuple(
            self.output_dir / path.relative_to(staging) for path in generated
        )
        return ReportResult(
            output_dir=self.output_dir,
            index_path=self.output_dir / "index.html",
            generated_files=final_files,
            source_artifact_ids=tuple(self._artifacts),
            incomplete=incomplete,
        )

    def _read_manifest(self) -> dict[str, Any]:
        try:
            value = json.loads(self.layout.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ReportBuildError(f"impossibile leggere il manifest: {error}") from error
        if not isinstance(value, dict):
            raise ReportBuildError("il manifest deve essere un oggetto JSON")
        return value

    def _validate_manifest_state(self) -> bool:
        if self.manifest.get("run_id") != self.layout.run_id:
            raise ReportBuildError("il manifest non appartiene al run selezionato")
        artifact_ids = self.manifest.get("artifact_ids")
        if not isinstance(artifact_ids, list) or any(
            not isinstance(item, str) for item in artifact_ids
        ):
            raise ReportBuildError("manifest artifact_ids non valido")
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ReportBuildError("manifest artifact_ids contiene duplicati")

        summary = self.manifest.get("task_summary", {})
        unfinished = (
            int(summary.get("PENDING", 0)) + int(summary.get("RUNNING", 0))
            if isinstance(summary, Mapping)
            else 0
        )
        incomplete = (
            self.manifest.get("status") != RunStatus.COMPLETE.value or unfinished > 0
        )
        if incomplete and not self.allow_incomplete:
            status = _text(self.manifest.get("status"), "UNKNOWN")
            raise ReportBuildError(
                f"manifest incompleto ({status}); impostare allow_incomplete=True "
                "per generare un report provvisorio"
            )
        return incomplete

    def _resolve_manifest_artifacts(self) -> tuple[Artifact, ...]:
        resolved: list[Artifact] = []
        for artifact_id in self.manifest["artifact_ids"]:
            try:
                path = self.registry.resolve(artifact_id, verify=True)
            except ArtifactError as error:
                raise ReportBuildError(
                    f"artifact manifest non valido {artifact_id}: {error}"
                ) from error
            artifact = self.registry.state.get_artifact(artifact_id)
            if artifact is None:  # defensive: resolve already enforces this
                raise ReportBuildError(f"artifact non registrato: {artifact_id}")
            self._artifacts[artifact_id] = artifact
            self._artifact_paths[artifact_id] = path
            resolved.append(artifact)
        return tuple(resolved)

    def _load_registered_data(
        self, artifacts: Iterable[Artifact]
    ) -> dict[str, list[dict[str, Any]]]:
        data: dict[str, list[dict[str, Any]]] = {
            "pages": [],
            "cases": [],
            "issues": [],
            "features": [],
            "coverage": [],
        }
        for artifact in artifacts:
            if artifact.media_type not in ("application/json", "text/json"):
                continue
            try:
                document = json.loads(
                    self._artifact_paths[artifact.id].read_text(encoding="utf-8")
                )
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ReportBuildError(
                    f"JSON registrato non leggibile: {artifact.relative_path}: {error}"
                ) from error
            self._merge_document(data, document, artifact)
        return data

    def _merge_document(
        self,
        data: dict[str, list[dict[str, Any]]],
        document: Any,
        artifact: Artifact,
    ) -> None:
        if isinstance(document, Mapping):
            recognized = False
            for source_key, destination_key in self._COLLECTION_KEYS.items():
                if source_key in document:
                    records = _as_records(document[source_key])
                    for record in records:
                        record.setdefault("_source_artifact_id", artifact.id)
                    data[destination_key].extend(records)
                    recognized = True
            if recognized:
                return

        role = next(
            (
                _text(artifact.metadata.get(key)).lower()
                for key in self._ROLE_KEYS
                if artifact.metadata.get(key)
            ),
            "",
        )
        if not role:
            role = Path(artifact.relative_path).stem.lower().replace("-", "_")
        aliases = {
            "page": "pages",
            "pages": "pages",
            "route": "pages",
            "routes": "pages",
            "case": "cases",
            "cases": "cases",
            "case_result": "cases",
            "case_results": "cases",
            "issue": "issues",
            "issues": "issues",
            "feature": "features",
            "features": "features",
            "coverage": "coverage",
        }
        destination = aliases.get(role)
        if destination is None:
            return
        records = _as_records(document)
        if isinstance(document, Mapping):
            records = [dict(document)]
        for record in records:
            record.setdefault("_source_artifact_id", artifact.id)
        data[destination].extend(records)

    def _normalize(self, data: dict[str, list[dict[str, Any]]]) -> None:
        for collection in ("pages", "cases", "issues", "features"):
            seen: set[str] = set()
            unique: list[dict[str, Any]] = []
            for index, record in enumerate(data[collection]):
                identifier = _text(record.get("id"), f"{collection}-{index + 1}")
                if identifier in seen:
                    continue
                record["id"] = identifier
                seen.add(identifier)
                unique.append(record)
            data[collection] = unique

        pages_by_id = {item["id"]: item for item in data["pages"]}
        cases_by_id = {item["id"]: item for item in data["cases"]}
        for case in data["cases"]:
            viewport = case.get("viewport")
            if not isinstance(viewport, Mapping):
                viewport = {}
                case["viewport"] = viewport
            width = int(viewport.get("width", 0) or 0)
            case["_viewport"] = (
                f"{width}×{int(viewport.get('height', 0) or 0)}" if width else "n/d"
            )
            case["_device"] = _text(
                case.get("device")
                or (case.get("metadata") or {}).get("device")
                if isinstance(case.get("metadata"), Mapping)
                else case.get("device")
            )
            if not case["_device"]:
                case["_device"] = (
                    "mobile"
                    if 0 < width < 768
                    else "tablet"
                    if 768 <= width < 1100
                    else "desktop"
                    if width >= 1100
                    else "n/d"
                )
            case["_artifacts"] = self._classify_artifacts(case.get("artifact_ids", []))

        for page in data["pages"]:
            metadata = page.get("metadata")
            if not isinstance(metadata, Mapping):
                metadata = {}
                page["metadata"] = metadata
            page["_cases"] = [
                case for case in data["cases"] if case.get("page_id") == page["id"]
            ]
            page["_issues"] = [
                issue
                for issue in data["issues"]
                if cases_by_id.get(_text(issue.get("case_result_id")), {}).get("page_id")
                == page["id"]
                or issue.get("page_id") == page["id"]
            ]
            page["_live_url"] = _text(page.get("live_url") or page.get("url"))
            page["_preview_url"] = _text(
                page.get("preview_url") or metadata.get("preview_url")
            )

        for issue in data["issues"]:
            case = cases_by_id.get(_text(issue.get("case_result_id")))
            page = pages_by_id.get(_text(issue.get("page_id")))
            if page is None and case is not None:
                page = pages_by_id.get(_text(case.get("page_id")))
            issue["_case"] = case
            issue["_page"] = page
            combined_ids = list(issue.get("artifact_ids", []))
            if case is not None:
                combined_ids.extend(case.get("artifact_ids", []))
            issue["_artifacts"] = self._classify_artifacts(combined_ids)

        if not data["features"]:
            names = {
                _text(case.get("feature") or case.get("scenario"))
                for case in data["cases"]
                if case.get("feature") or case.get("scenario")
            }
            data["features"] = [
                {"id": _slug(name), "name": name, "description": ""}
                for name in sorted(names)
            ]
        for feature in data["features"]:
            name = _text(feature.get("name") or feature.get("title") or feature["id"])
            feature["name"] = name
            feature["_cases"] = [
                case
                for case in data["cases"]
                if _text(case.get("feature") or case.get("scenario")) in (name, feature["id"])
            ]
            case_ids = {case["id"] for case in feature["_cases"]}
            feature["_issues"] = [
                issue
                for issue in data["issues"]
                if issue.get("feature") in (name, feature["id"])
                or issue.get("case_result_id") in case_ids
            ]

        referenced_ids: set[str] = set()
        for collection in ("pages", "cases", "issues", "features", "coverage"):
            for record in data[collection]:
                values = record.get("artifact_ids", [])
                if isinstance(values, list):
                    referenced_ids.update(item for item in values if isinstance(item, str))
        missing_from_manifest = referenced_ids - set(self._artifacts)
        if missing_from_manifest:
            joined = ", ".join(sorted(missing_from_manifest))
            raise ReportBuildError(
                f"artifact referenziati dai dati ma assenti dal manifest: {joined}"
            )
        for artifact_id in referenced_ids:
            try:
                self.registry.resolve(artifact_id, verify=True)
            except ArtifactError as error:
                raise ReportBuildError(f"artifact referenziato non valido: {error}") from error

    def _classify_artifacts(self, artifact_ids: Any) -> dict[str, Artifact]:
        result: dict[str, Artifact] = {}
        if not isinstance(artifact_ids, (list, tuple)):
            return result
        for artifact_id in artifact_ids:
            artifact = self._artifacts.get(_text(artifact_id))
            if artifact is None:
                continue
            metadata = artifact.metadata
            role = _text(
                metadata.get("role")
                or metadata.get("side")
                or metadata.get("target")
                or metadata.get("report_role")
            ).lower()
            name = artifact.relative_path.lower()
            candidates = (
                ("heatmap", "heatmap"),
                ("diff", "diff"),
                ("preview", "preview"),
                ("live", "live"),
                ("baseline", "live"),
                ("trace", "trace"),
                ("raw", "raw"),
            )
            key = next(
                (target for marker, target in candidates if marker in role or marker in name),
                "",
            )
            if not key and artifact.media_type.startswith("image/"):
                key = "preview" if "live" in result else "live"
            if key:
                result.setdefault(key, artifact)
        return result

    def _render(
        self,
        root: Path,
        data: dict[str, list[dict[str, Any]]],
        incomplete: bool,
    ) -> list[Path]:
        for directory in (
            "assets",
            "routes",
            "features",
            "issues",
            "data/routes",
            "data/issues",
        ):
            (root / directory).mkdir(parents=True, exist_ok=True)
        asset_source = Path(__file__).resolve().parents[1] / "report_assets"
        generated: list[Path] = []
        for name in ("report.css", "report.js"):
            destination = root / "assets" / name
            destination.write_bytes((asset_source / name).read_bytes())
            generated.append(destination)

        page_slugs = _unique_slugs(data["pages"])
        feature_slugs = _unique_slugs(data["features"])
        issue_slugs = _unique_slugs(data["issues"])

        index = root / "index.html"
        index.write_text(
            self._index_html(
                data, page_slugs, feature_slugs, issue_slugs, incomplete
            ),
            encoding="utf-8",
        )
        generated.append(index)
        coverage = root / "coverage.html"
        coverage.write_text(
            self._coverage_html(data, page_slugs, incomplete), encoding="utf-8"
        )
        generated.append(coverage)

        for index_number, page in enumerate(data["pages"]):
            slug = page_slugs[page["id"]]
            route_path = root / "routes" / f"{slug}.html"
            route_path.write_text(
                self._route_html(
                    page,
                    page_slugs,
                    issue_slugs,
                    index_number,
                    data["pages"],
                    incomplete,
                    route_path,
                ),
                encoding="utf-8",
            )
            generated.append(route_path)
            raw_path = root / "data" / "routes" / f"{slug}.json"
            raw_path.write_text(
                json.dumps(self._public_record(page), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            generated.append(raw_path)

        for index_number, feature in enumerate(data["features"]):
            path = root / "features" / f"{feature_slugs[feature['id']]}.html"
            path.write_text(
                self._feature_html(
                    feature,
                    feature_slugs,
                    issue_slugs,
                    index_number,
                    data["features"],
                    incomplete,
                ),
                encoding="utf-8",
            )
            generated.append(path)

        for index_number, issue in enumerate(data["issues"]):
            slug = issue_slugs[issue["id"]]
            path = root / "issues" / f"{slug}.html"
            path.write_text(
                self._issue_html(
                    issue,
                    issue_slugs,
                    page_slugs,
                    index_number,
                    data["issues"],
                    incomplete,
                    path,
                ),
                encoding="utf-8",
            )
            generated.append(path)
            raw_path = root / "data" / "issues" / f"{slug}.json"
            raw_path.write_text(
                json.dumps(self._public_record(issue), ensure_ascii=False, indent=2)
                + "\n",
                encoding="utf-8",
            )
            generated.append(raw_path)
        return generated

    @staticmethod
    def _public_record(record: Mapping[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in record.items() if not key.startswith("_")}

    def _shell(
        self,
        *,
        title: str,
        body: str,
        depth: int,
        incomplete: bool,
        filters: bool = False,
    ) -> str:
        prefix = "../" * depth
        banner = (
            '<aside class="incomplete" role="alert"><strong>REPORT INCOMPLETO</strong>'
            "<span>I dati provengono da un run non concluso e possono cambiare.</span></aside>"
            if incomplete
            else ""
        )
        filter_markup = self._filters() if filters else ""
        return (
            "<!doctype html><html lang=\"it\"><head><meta charset=\"utf-8\">"
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{escape(title)} · Store parity</title>"
            f'<link rel="stylesheet" href="{prefix}assets/report.css"></head>'
            '<body><a class="skip" href="#contenuto">Vai al contenuto</a>'
            f"{banner}<header class=\"site-header\"><a class=\"brand\" href=\"{prefix}index.html\">"
            "Gray Matters <span>Store parity</span></a><nav>"
            f'<a href="{prefix}index.html">Panoramica</a>'
            f'<a href="{prefix}coverage.html">Copertura</a></nav></header>'
            f"{filter_markup}<main id=\"contenuto\">{body}</main>"
            '<footer>Report statico · Tutti gli artifact sono verificati con SHA-256.</footer>'
            f'<script src="{prefix}assets/report.js" defer></script></body></html>'
        )

    @staticmethod
    def _filters() -> str:
        fields = (
            ("severity", "Severità"),
            ("status", "Stato"),
            ("device", "Dispositivo"),
            ("viewport", "Viewport"),
            ("route", "Route"),
            ("page-type", "Tipo pagina"),
            ("feature", "Feature"),
            ("check", "Check"),
        )
        selects = "".join(
            f'<label>{label}<select data-filter="{name}">'
            f'<option value="">Tutti</option></select></label>'
            for name, label in fields
        )
        return (
            '<section class="filters" data-filter-panel><button type="button" '
            'class="filter-toggle" data-filter-toggle>Filtri</button>'
            f'<div class="filter-grid">{selects}<button type="button" '
            'data-filter-reset>Reimposta</button></div>'
            '<p class="filter-count" data-filter-count aria-live="polite"></p></section>'
        )

    def _index_html(
        self,
        data: dict[str, list[dict[str, Any]]],
        page_slugs: Mapping[str, str],
        feature_slugs: Mapping[str, str],
        issue_slugs: Mapping[str, str],
        incomplete: bool,
    ) -> str:
        failing = sum(
            1 for case in data["cases"] if _text(case.get("status")).upper() not in ("PASSED", "SKIPPED")
        )
        hero = (
            '<section class="hero"><p class="eyebrow">Audit di parità visuale</p>'
            f"<h1>Report run {escape(self.layout.run_id)}</h1>"
            "<p>Confronto navigabile tra store live e tema preview, con evidenze "
            "tecniche consultabili senza servizi esterni.</p></section>"
            '<section class="metrics">'
            f'<article><strong>{len(data["pages"])}</strong><span>Route</span></article>'
            f'<article><strong>{len(data["cases"])}</strong><span>Verifiche</span></article>'
            f'<article><strong>{failing}</strong><span>Non conformi</span></article>'
            f'<article><strong>{len(data["issues"])}</strong><span>Issue</span></article>'
            "</section>"
        )
        routes = "".join(
            self._route_card(page, page_slugs[page["id"]]) for page in data["pages"]
        ) or '<p class="empty">Nessuna route registrata nel manifest.</p>'
        issues = "".join(
            self._issue_card(issue, f"issues/{issue_slugs[issue['id']]}.html")
            for issue in data["issues"]
        ) or '<p class="empty">Nessuna issue registrata.</p>'
        features = "".join(
            '<article class="route-card"><a href="features/'
            f'{feature_slugs[feature["id"]]}.html"><span class="type">Feature</span>'
            f'<h3>{escape(feature["name"])}</h3>'
            f'<p>{len(feature["_cases"])} check · {len(feature["_issues"])} issue</p>'
            "</a></article>"
            for feature in data["features"]
        ) or '<p class="empty">Nessuna feature registrata.</p>'
        body = (
            hero
            + '<section><div class="section-heading"><h2>Route</h2>'
            '<a href="coverage.html">Vedi matrice di copertura →</a></div>'
            f'<div class="card-grid" data-filter-list>{routes}</div></section>'
            '<section><div class="section-heading"><h2>Issue prioritarie</h2></div>'
            f'<div class="issue-list" data-filter-list>{issues}</div></section>'
            '<section><div class="section-heading"><h2>Feature</h2></div>'
            f'<div class="card-grid">{features}</div></section>'
        )
        return self._shell(
            title="Panoramica",
            body=body,
            depth=0,
            incomplete=incomplete,
            filters=True,
        )

    def _coverage_html(
        self,
        data: dict[str, list[dict[str, Any]]],
        page_slugs: Mapping[str, str],
        incomplete: bool,
    ) -> str:
        rows = []
        pages = {page["id"]: page for page in data["pages"]}
        for case in data["cases"]:
            page = pages.get(_text(case.get("page_id")), {})
            route = _text(page.get("path"), "Route non disponibile")
            href = (
                f"routes/{page_slugs[page['id']]}.html"
                if page.get("id") in page_slugs
                else "index.html"
            )
            attrs = self._filter_attrs(page=page, case=case)
            rows.append(
                f'<tr data-filter-item {attrs}><td><a href="{href}">{escape(route)}</a></td>'
                f"<td>{escape(_text(page.get('page_type'), 'other'))}</td>"
                f"<td>{escape(_text(case.get('scenario'), '—'))}</td>"
                f"<td>{escape(case['_device'])}</td><td>{escape(case['_viewport'])}</td>"
                f"<td>{self._status(case.get('status'))}</td></tr>"
            )
        table = (
            '<div class="table-wrap"><table><thead><tr><th>Route</th><th>Tipo</th>'
            "<th>Check</th><th>Dispositivo</th><th>Viewport</th><th>Stato</th>"
            f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            if rows
            else '<p class="empty">Nessuna verifica disponibile.</p>'
        )
        body = (
            '<section class="page-title"><p class="eyebrow">Copertura</p>'
            "<h1>Matrice delle verifiche</h1><p>Route, viewport e scenari inclusi "
            f"nel run.</p></section><section data-filter-list>{table}</section>"
        )
        return self._shell(
            title="Copertura",
            body=body,
            depth=0,
            incomplete=incomplete,
            filters=True,
        )

    def _route_card(self, page: Mapping[str, Any], slug: str) -> str:
        cases = page["_cases"]
        failed = sum(
            1 for case in cases if _text(case.get("status")).upper() not in ("PASSED", "SKIPPED")
        )
        attrs = self._filter_attrs(page=page)
        return (
            f'<article class="route-card" data-filter-item {attrs}>'
            f'<a href="routes/{slug}.html"><span class="type">'
            f"{escape(_text(page.get('page_type'), 'other'))}</span>"
            f"<h3>{escape(_text(page.get('path'), page['id']))}</h3>"
            f"<p>{len(cases)} verifiche · {failed} non conformi</p></a></article>"
        )

    def _route_html(
        self,
        page: dict[str, Any],
        page_slugs: Mapping[str, str],
        issue_slugs: Mapping[str, str],
        index: int,
        pages: Sequence[dict[str, Any]],
        incomplete: bool,
        output_path: Path,
    ) -> str:
        links = self._external_links(page["_live_url"], page["_preview_url"])
        raw = f'../data/routes/{page_slugs[page["id"]]}.json'
        comparisons = []
        for case in page["_cases"]:
            attrs = self._filter_attrs(page=page, case=case)
            comparisons.append(
                f'<article class="comparison-card" data-filter-item {attrs}>'
                '<div class="comparison-heading">'
                f"<div><p class=\"eyebrow\">{escape(_text(case.get('scenario'), 'Check'))}</p>"
                f"<h2>{escape(case['_device'])} · {escape(case['_viewport'])}</h2></div>"
                f"{self._status(case.get('status'))}</div>"
                f"{self._viewer(case['_artifacts'], output_path)}"
                f"{self._technical(case, raw)}</article>"
            )
        issue_cards = "".join(
            self._issue_card(issue, f"../issues/{issue_slugs[issue['id']]}.html")
            for issue in page["_issues"]
        )
        body = (
            self._prev_next(index, pages, page_slugs, "routes")
            + '<section class="page-title"><p class="eyebrow">Route</p>'
            f"<h1>{escape(_text(page.get('path'), page['id']))}</h1>"
            f"<p>Tipo pagina: {escape(_text(page.get('page_type'), 'other'))}</p>"
            f'<div class="actions">{links}<a href="{raw}">JSON grezzo</a></div></section>'
            f'<section data-filter-list>{"".join(comparisons) or self._empty_viewer()}</section>'
            '<section><div class="section-heading"><h2>Issue della route</h2></div>'
            f'<div class="issue-list">{issue_cards or "<p class=empty>Nessuna issue.</p>"}</div>'
            "</section>"
        )
        return self._shell(
            title=_text(page.get("path"), "Route"),
            body=body,
            depth=1,
            incomplete=incomplete,
            filters=True,
        )

    def _feature_html(
        self,
        feature: dict[str, Any],
        feature_slugs: Mapping[str, str],
        issue_slugs: Mapping[str, str],
        index: int,
        features: Sequence[dict[str, Any]],
        incomplete: bool,
    ) -> str:
        checks = "".join(
            f'<li data-filter-item {self._filter_attrs(case=case)}>'
            f"<strong>{escape(_text(case.get('scenario'), 'Check'))}</strong>"
            f"<span>{escape(case['_device'])} · {escape(case['_viewport'])}</span>"
            f"{self._status(case.get('status'))}</li>"
            for case in feature["_cases"]
        )
        issues = "".join(
            self._issue_card(issue, f"../issues/{issue_slugs[issue['id']]}.html")
            for issue in feature["_issues"]
        )
        body = (
            self._prev_next(index, features, feature_slugs, "features")
            + '<section class="page-title"><p class="eyebrow">Feature</p>'
            f"<h1>{escape(feature['name'])}</h1>"
            f"<p>{escape(_text(feature.get('description'), 'Risultati aggregati della feature.'))}</p>"
            f'</section><section><h2>Check eseguiti</h2><ul class="check-list" '
            f'data-filter-list>{checks or "<li class=empty>Nessun check.</li>"}</ul></section>'
            f'<section><h2>Issue</h2><div class="issue-list">{issues or "<p class=empty>Nessuna issue.</p>"}</div></section>'
        )
        return self._shell(
            title=feature["name"],
            body=body,
            depth=1,
            incomplete=incomplete,
            filters=True,
        )

    def _issue_html(
        self,
        issue: dict[str, Any],
        issue_slugs: Mapping[str, str],
        page_slugs: Mapping[str, str],
        index: int,
        issues: Sequence[dict[str, Any]],
        incomplete: bool,
        output_path: Path,
    ) -> str:
        page = issue["_page"] or {}
        route_link = (
            f'../routes/{page_slugs[page["id"]]}.html'
            if page.get("id") in page_slugs
            else "../index.html"
        )
        trace = self._artifact_link(issue["_artifacts"].get("trace"), output_path, "Trace")
        raw = f'../data/issues/{issue_slugs[issue["id"]]}.json'
        body = (
            self._prev_next(index, issues, issue_slugs, "issues")
            + '<article class="issue-detail"><header>'
            f'<span class="severity severity-{escape(_text(issue.get("severity"), "info"))}">'
            f'{escape(_text(issue.get("severity"), "info"))}</span>'
            f"<h1>{escape(_text(issue.get('title'), issue['id']))}</h1>"
            f'<p><a href="{route_link}">{escape(_text(page.get("path"), "Route"))}</a>'
            f" · {escape(_text(issue.get('category'), 'generale'))}</p></header>"
            '<div class="tabs" data-tabs><div role="tablist">'
            '<button role="tab" aria-selected="true" data-tab="summary">Sintesi</button>'
            '<button role="tab" aria-selected="false" data-tab="technical">Dettagli tecnici</button>'
            '</div><section role="tabpanel" data-panel="summary">'
            f"<p>{escape(_text(issue.get('description'), 'Descrizione non disponibile.'))}</p>"
            "</section><section role=\"tabpanel\" data-panel=\"technical\" hidden>"
            f"<dl><dt>Issue ID</dt><dd>{escape(issue['id'])}</dd>"
            f"<dt>Case ID</dt><dd>{escape(_text(issue.get('case_result_id'), '—'))}</dd>"
            f"<dt>Selettore</dt><dd><code>{escape(_text(issue.get('selector'), '—'))}</code></dd>"
            f"<dt>Categoria</dt><dd>{escape(_text(issue.get('category'), '—'))}</dd></dl>"
            f'<div class="actions"><a href="{raw}">JSON grezzo</a>{trace}</div>'
            "</section></div>"
            f"{self._viewer(issue['_artifacts'], output_path)}</article>"
        )
        return self._shell(
            title=_text(issue.get("title"), "Issue"),
            body=body,
            depth=1,
            incomplete=incomplete,
        )

    def _viewer(self, artifacts: Mapping[str, Artifact], output_path: Path) -> str:
        live = artifacts.get("live")
        preview = artifacts.get("preview")
        if live is None and preview is None:
            return self._empty_viewer()
        live_src = self._artifact_href(live, output_path) if live else ""
        preview_src = self._artifact_href(preview, output_path) if preview else ""
        diff_src = self._artifact_href(artifacts.get("diff"), output_path)
        heat_src = self._artifact_href(artifacts.get("heatmap"), output_path)
        mode_buttons = [
            '<button type="button" data-view-mode="side" aria-pressed="true">Affiancato</button>',
            '<button type="button" data-view-mode="slider">Slider</button>',
            '<button type="button" data-view-mode="overlay">Overlay</button>',
            '<button type="button" data-view-mode="blink">Blink</button>',
        ]
        if diff_src:
            mode_buttons.append('<button type="button" data-view-mode="diff">Diff</button>')
        if heat_src:
            mode_buttons.append('<button type="button" data-view-mode="heatmap">Heatmap</button>')
        layers = (
            self._image(live_src, "Store live", "live")
            + self._image(preview_src, "Tema preview", "preview")
            + self._image(diff_src, "Diff visuale", "diff")
            + self._image(heat_src, "Heatmap", "heatmap")
        )
        return (
            '<div class="viewer" data-viewer data-mode="side"><div class="viewer-tools">'
            f'<div class="mode-buttons">{"".join(mode_buttons)}</div>'
            '<label>Zoom <input type="range" min="50" max="300" value="100" '
            'step="10" data-zoom></label><button type="button" data-reset-view>Reimposta vista</button>'
            '</div><div class="viewer-stage" data-view-stage>'
            f'{layers}<input class="slider-control" type="range" min="0" max="100" '
            'value="50" aria-label="Posizione cursore confronto" data-compare-slider>'
            '<span class="viewer-label live-label">Live</span>'
            '<span class="viewer-label preview-label">Preview</span></div></div>'
        )

    @staticmethod
    def _image(src: str, label: str, role: str) -> str:
        if not src:
            return ""
        return (
            f'<div class="image-layer layer-{role}" data-layer="{role}">'
            f'<img src="{escape(src, quote=True)}" alt="{escape(label)}" loading="lazy"></div>'
        )

    @staticmethod
    def _empty_viewer() -> str:
        return (
            '<div class="empty viewer-empty"><strong>Evidenza visuale non disponibile</strong>'
            "<span>Il manifest non include screenshot per questo elemento.</span></div>"
        )

    def _technical(self, case: Mapping[str, Any], raw_href: str) -> str:
        trace = self._artifact_link(
            case["_artifacts"].get("trace"),
            self.output_dir / "routes" / "placeholder.html",
            "Trace",
        )
        metrics = case.get("metrics")
        metrics_json = json.dumps(
            metrics if isinstance(metrics, Mapping) else {},
            ensure_ascii=False,
            sort_keys=True,
        )
        return (
            '<details class="technical"><summary>Dettagli tecnici</summary><dl>'
            f"<dt>Case ID</dt><dd>{escape(case['id'])}</dd>"
            f"<dt>Profilo</dt><dd>{escape(_text(case.get('profile'), '—'))}</dd>"
            f"<dt>Metriche</dt><dd><code>{escape(metrics_json)}</code></dd>"
            f"<dt>Errore</dt><dd>{escape(_text(case.get('error'), '—'))}</dd></dl>"
            f'<div class="actions"><a href="{raw_href}">JSON grezzo</a>{trace}</div></details>'
        )

    def _issue_card(self, issue: Mapping[str, Any], href: str) -> str:
        page = issue.get("_page") or {}
        case = issue.get("_case") or {}
        attrs = self._filter_attrs(page=page, case=case, issue=issue)
        severity = _text(issue.get("severity"), "info")
        return (
            f'<article class="issue-card" data-filter-item {attrs}>'
            f'<a href="{href}"><span class="severity severity-{escape(severity)}">'
            f"{escape(severity)}</span><div><h3>"
            f"{escape(_text(issue.get('title'), issue.get('id')))}</h3>"
            f"<p>{escape(_text(page.get('path'), 'Route non disponibile'))} · "
            f"{escape(_text(issue.get('category'), 'generale'))}</p></div></a></article>"
        )

    @staticmethod
    def _status(value: Any) -> str:
        status = _text(value, "UNKNOWN").upper()
        return f'<span class="status status-{escape(status.lower())}">{escape(status)}</span>'

    def _filter_attrs(
        self,
        *,
        page: Mapping[str, Any] | None = None,
        case: Mapping[str, Any] | None = None,
        issue: Mapping[str, Any] | None = None,
    ) -> str:
        page = page or {}
        case = case or {}
        issue = issue or {}
        values = {
            "severity": issue.get("severity"),
            "status": issue.get("status") or case.get("status"),
            "device": case.get("_device") or case.get("device"),
            "viewport": case.get("_viewport"),
            "route": page.get("path"),
            "page-type": page.get("page_type"),
            "feature": issue.get("feature") or case.get("feature") or case.get("scenario"),
            "check": issue.get("check") or case.get("check") or case.get("scenario"),
        }
        return " ".join(
            f'data-{key}="{escape(_text(value), quote=True)}"'
            for key, value in values.items()
            if value not in (None, "")
        )

    @staticmethod
    def _external_links(live: str, preview: str) -> str:
        links = []
        if live:
            links.append(
                f'<a href="{escape(live, quote=True)}" rel="noopener">Apri live ↗</a>'
            )
        if preview:
            links.append(
                f'<a href="{escape(preview, quote=True)}" rel="noopener">Apri preview ↗</a>'
            )
        return "".join(links)

    def _artifact_href(self, artifact: Artifact | None, output_path: Path) -> str:
        if artifact is None:
            return ""
        path = self._artifact_paths[artifact.id]
        return Path(os.path.relpath(path, output_path.parent)).as_posix()

    def _artifact_link(
        self, artifact: Artifact | None, output_path: Path, label: str
    ) -> str:
        if artifact is None:
            return ""
        href = self._artifact_href(artifact, output_path)
        return f'<a href="{escape(href, quote=True)}">{escape(label)}</a>'

    @staticmethod
    def _prev_next(
        index: int,
        records: Sequence[Mapping[str, Any]],
        slugs: Mapping[str, str],
        directory: str,
    ) -> str:
        links = []
        if index > 0:
            previous = records[index - 1]
            links.append(
                f'<a rel="prev" href="{slugs[_text(previous["id"])]}.html">← Precedente</a>'
            )
        else:
            links.append("<span></span>")
        if index + 1 < len(records):
            following = records[index + 1]
            links.append(
                f'<a rel="next" href="{slugs[_text(following["id"])]}.html">Successivo →</a>'
            )
        else:
            links.append("<span></span>")
        return f'<nav class="prev-next" aria-label="Navigazione {escape(directory)}">{"".join(links)}</nav>'


def build_report(
    registry_or_layout: ArtifactRegistry | RunLayout,
    *,
    manifest: Mapping[str, Any] | None = None,
    output_dir: str | Path | None = None,
    allow_incomplete: bool = False,
) -> ReportResult:
    """Build a report using only explicit manifest artifact IDs.

    ``registry_or_layout`` may be an existing :class:`ArtifactRegistry` or a
    :class:`RunLayout`, in which case a registry is opened for that run.
    """

    registry = (
        registry_or_layout
        if isinstance(registry_or_layout, ArtifactRegistry)
        else ArtifactRegistry(registry_or_layout)
    )
    return ReportBuilder(
        registry,
        manifest=manifest,
        output_dir=output_dir,
        allow_incomplete=allow_incomplete,
    ).build()


_LINK_PATTERN = re.compile(
    r"""(?:href|src)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE
)
_ID_PATTERN = re.compile(r"""\bid\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)


def validate_report_links(report_dir: str | Path, *, allowed_root: str | Path | None = None) -> None:
    """Validate local links in every generated HTML file without directory globs."""

    root = Path(report_dir).resolve()
    boundary = Path(allowed_root).resolve() if allowed_root is not None else root
    if not root.is_dir():
        raise ReportBuildError(f"directory report inesistente: {root}")

    html_files: list[Path] = []
    pending = [root]
    while pending:
        directory = pending.pop()
        for child in directory.iterdir():
            if child.is_dir():
                pending.append(child)
            elif child.suffix.lower() == ".html":
                html_files.append(child)

    errors: list[str] = []
    ids_by_path: dict[Path, set[str]] = {}
    for html_file in html_files:
        content = html_file.read_text(encoding="utf-8")
        ids_by_path[html_file.resolve()] = {
            first or second for first, second in _ID_PATTERN.findall(content)
        }

    for html_file in html_files:
        content = html_file.read_text(encoding="utf-8")
        for first, second in _LINK_PATTERN.findall(content):
            raw = first or second
            parsed = urlsplit(raw)
            if parsed.scheme in ("http", "https", "mailto", "tel", "data") or raw.startswith("//"):
                continue
            decoded_path = unquote(parsed.path)
            target = (
                html_file.resolve()
                if not decoded_path
                else (html_file.parent / decoded_path).resolve()
            )
            inside_report = target == root or root in target.parents
            inside_boundary = target == boundary or boundary in target.parents
            if not inside_report and not inside_boundary:
                errors.append(f"{html_file.relative_to(root)}: link fuori run {raw}")
                continue
            if not target.is_file():
                errors.append(f"{html_file.relative_to(root)}: link mancante {raw}")
                continue
            if parsed.fragment and target.suffix.lower() == ".html":
                target_ids = ids_by_path.get(target)
                if target_ids is None:
                    target_content = target.read_text(encoding="utf-8")
                    target_ids = {
                        a or b for a, b in _ID_PATTERN.findall(target_content)
                    }
                    ids_by_path[target] = target_ids
                if unquote(parsed.fragment) not in target_ids:
                    errors.append(
                        f"{html_file.relative_to(root)}: ancora mancante {raw}"
                    )
    if errors:
        raise ReportBuildError("link interni non validi:\n" + "\n".join(sorted(errors)))
