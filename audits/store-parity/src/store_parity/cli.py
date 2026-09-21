from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from store_parity.artifacts import ArtifactRegistry
from store_parity.config import ConfigError, load_config
from store_parity.layout import LayoutError, RunLayout
from store_parity.manifest import ManifestError, ManifestLifecycle
from store_parity.models import ArtifactKind
from store_parity.runner import AuditRunner, RunnerOptions
from store_parity.state import StateError, TaskStateStore


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="store-parity",
        description="Full-store live-versus-preview UI/UX parity audit",
    )
    parser.add_argument("--version", action="version", version="store-parity 0.1.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="execute an immutable audit run")
    run.add_argument("--config", type=Path, default=Path("config/default.yml"))
    run.add_argument("--runs-dir", type=Path, default=Path("runs"))
    run.add_argument("--run-id")
    run.add_argument("--label")
    run.add_argument(
        "--resume",
        type=Path,
        metavar="RUN_DIR",
        help="resume an existing non-complete run directory",
    )
    run.add_argument(
        "--profile",
        choices=("mobile-p0", "smoke", "full"),
        default="smoke",
    )
    run.add_argument(
        "--path",
        dest="paths",
        action="append",
        default=[],
        help="audit an explicit path/URL instead of crawling (repeatable)",
    )
    run.add_argument("--max-representative-routes", type=_positive_int)
    run.add_argument("--max-cases", type=_positive_int)
    run.add_argument("--retry-failed", action="store_true")
    run.add_argument(
        "--allow-incomplete-report",
        action="store_true",
        help="generate a provisional report when execution fails",
    )
    run.set_defaults(handler=_run)

    for command in ("discover", "capture", "compare"):
        stage = subparsers.add_parser(
            command, help=f"reserved {command} stage interface"
        )
        stage.add_argument("run_dir", type=Path)
        stage.set_defaults(handler=_reserved_stage)

    report = subparsers.add_parser(
        "report", help="list registered report inputs without filesystem discovery"
    )
    report.add_argument("run_dir", type=Path)
    report.add_argument("--kind", choices=[kind.value for kind in ArtifactKind])
    report.add_argument("--verify", action="store_true")
    report.set_defaults(handler=_report)

    status = subparsers.add_parser("status", help="show run and task status")
    status.add_argument("run_dir", type=Path)
    status.set_defaults(handler=_status)
    return parser


def _run(arguments: argparse.Namespace) -> int:
    config = load_config(arguments.config)
    if arguments.resume and arguments.run_id:
        raise LayoutError("--resume and --run-id cannot be used together")
    if arguments.resume and arguments.paths:
        raise LayoutError("--path cannot change an existing resumed plan")
    resume = arguments.resume is not None
    if resume:
        layout = RunLayout.open(arguments.resume)
    else:
        run_id = arguments.run_id or _generated_run_id(arguments.label)
        layout = RunLayout.create(arguments.runs_dir, run_id)
    options = RunnerOptions(
        profile=arguments.profile,
        explicit_paths=tuple(arguments.paths),
        max_representative_routes=arguments.max_representative_routes,
        max_cases=arguments.max_cases,
        retry_failed=arguments.retry_failed,
        allow_incomplete_report=arguments.allow_incomplete_report,
    )
    result = asyncio.run(
        AuditRunner(
            config,
            layout,
            options,
            resume=resume,
        ).run()
    )
    print(json.dumps(result.to_dict(), sort_keys=True))
    return 0 if result.status == "COMPLETE" and result.accepted else 1


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return number


def _generated_run_id(label: str | None) -> str:
    prefix = ""
    if label:
        prefix = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip(".-_")
        if not prefix:
            raise LayoutError("label must contain a letter or number")
        prefix += "-"
    return (
        prefix
        + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        + f"-{uuid.uuid4().hex[:8]}"
    )


def _reserved_stage(arguments: argparse.Namespace) -> int:
    layout = RunLayout.open(arguments.run_dir)
    print(
        json.dumps(
            {
                "command": arguments.command,
                "run_id": layout.run_id,
                "status": "reserved-for-runtime-agent",
            },
            sort_keys=True,
        )
    )
    return 0


def _report(arguments: argparse.Namespace) -> int:
    layout = RunLayout.open(arguments.run_dir)
    registry = ArtifactRegistry(layout)
    kind = ArtifactKind(arguments.kind) if arguments.kind else None
    artifacts = registry.list_registered(kind=kind, verify=arguments.verify)
    print(
        json.dumps(
            {
                "run_id": layout.run_id,
                "source": "artifact-registry",
                "artifacts": [artifact.to_dict() for artifact in artifacts],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _status(arguments: argparse.Namespace) -> int:
    layout = RunLayout.open(arguments.run_dir)
    state = TaskStateStore(layout.state_db)
    manifest_status = None
    if layout.manifest_path.is_file():
        registry = ArtifactRegistry(layout, state)
        manifest_status = ManifestLifecycle(layout, registry, state).read().get("status")
    print(
        json.dumps(
            {
                "run_id": layout.run_id,
                "manifest_status": manifest_status,
                "tasks": state.counts(),
                "registered_artifacts": len(state.list_artifacts()),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    arguments = parser.parse_args(argv)
    try:
        return int(arguments.handler(arguments))
    except (ConfigError, LayoutError, StateError, ManifestError, OSError) as error:
        parser.exit(2, f"store-parity: error: {error}\n")


if __name__ == "__main__":
    sys.exit(main())
