from __future__ import annotations

from pathlib import Path

import yaml

from store_parity.config import load_config


def _config() -> dict:
    return {
        "version": 1,
        "targets": {
            "live": {"base_url": "https://example.com"},
            "preview": {
                "base_url": "https://example.com",
                "theme_id": 187054457141,
            },
        },
        "viewports": {"breakpoint_probes": [390, 768, 1280]},
        "scenarios": {
            "profiles": {
                "mobile-p0": {
                    "scenarios": ["baseline"],
                    "viewports": ["mobile"],
                },
                "smoke": {
                    "scenarios": ["baseline"],
                    "viewports": ["mobile", "desktop"],
                },
                "full": {
                    "scenarios": ["baseline"],
                    "viewports": ["mobile", "desktop", "breakpoint_probes"],
                },
            }
        },
    }


def test_config_digest_is_stable_across_yaml_formatting(tmp_path: Path) -> None:
    first = tmp_path / "first.yml"
    second = tmp_path / "second.yml"
    value = _config()
    first.write_text(yaml.safe_dump(value, sort_keys=True), encoding="utf-8")
    second.write_text(
        yaml.safe_dump(
            {
                "scenarios": value["scenarios"],
                "viewports": value["viewports"],
                "targets": value["targets"],
                "version": value["version"],
            },
            sort_keys=False,
            default_flow_style=True,
        ),
        encoding="utf-8",
    )

    first_config = load_config(first)
    second_config = load_config(second)

    assert first_config.digest == second_config.digest
    assert len(first_config.digest) == 64
