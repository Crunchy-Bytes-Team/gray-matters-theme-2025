from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import yaml


class ConfigError(ValueError):
    """Raised when audit configuration is missing or malformed."""


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def config_digest(data: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _thaw(data),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True, slots=True)
class LoadedConfig:
    path: Path
    data: Mapping[str, Any]
    digest: str

    def mutable_copy(self) -> dict[str, Any]:
        return _thaw(self.data)


def _require_mapping(parent: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise ConfigError(f"configuration key '{key}' must be a mapping")
    return value


def _validate(data: Mapping[str, Any]) -> None:
    if data.get("version") != 1:
        raise ConfigError("configuration version must be 1")

    targets = _require_mapping(data, "targets")
    for target_name in ("live", "preview"):
        target = _require_mapping(targets, target_name)
        base_url = target.get("base_url")
        if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
            raise ConfigError(f"targets.{target_name}.base_url must be an HTTP URL")

    preview = _require_mapping(targets, "preview")
    if not isinstance(preview.get("theme_id"), int):
        raise ConfigError("targets.preview.theme_id must be an integer")

    scenarios = _require_mapping(data, "scenarios")
    profiles = _require_mapping(scenarios, "profiles")
    missing_profiles = {"mobile-p0", "smoke", "full"} - set(profiles)
    if missing_profiles:
        missing = ", ".join(sorted(missing_profiles))
        raise ConfigError(f"missing scenario profiles: {missing}")
    from store_parity.scenarios.definitions import SCENARIO_DEFINITIONS

    allowed_viewports = {"mobile", "desktop", "breakpoint_probes"}
    for profile_name, raw_profile in profiles.items():
        if not isinstance(raw_profile, Mapping):
            raise ConfigError(
                f"scenarios.profiles.{profile_name} must be a mapping"
            )
        profile_scenarios = raw_profile.get("scenarios")
        if not isinstance(profile_scenarios, (list, tuple)) or not profile_scenarios:
            raise ConfigError(
                f"scenarios.profiles.{profile_name}.scenarios must be a non-empty list"
            )
        unknown_scenarios = set(profile_scenarios) - set(SCENARIO_DEFINITIONS)
        if unknown_scenarios:
            raise ConfigError(
                f"scenarios.profiles.{profile_name} contains unknown scenarios: "
                f"{', '.join(sorted(unknown_scenarios))}"
            )
        profile_viewports = raw_profile.get("viewports")
        if not isinstance(profile_viewports, (list, tuple)) or not profile_viewports:
            raise ConfigError(
                f"scenarios.profiles.{profile_name}.viewports must be a non-empty list"
            )
        unknown_viewports = set(profile_viewports) - allowed_viewports
        if unknown_viewports:
            raise ConfigError(
                f"scenarios.profiles.{profile_name} contains unknown viewports: "
                f"{', '.join(sorted(unknown_viewports))}"
            )

    viewports = _require_mapping(data, "viewports")
    probes = viewports.get("breakpoint_probes")
    if not isinstance(probes, (list, tuple)) or not all(
        isinstance(width, int) and width > 0 for width in probes
    ):
        raise ConfigError("viewports.breakpoint_probes must contain positive integers")


def load_config(path: str | Path) -> LoadedConfig:
    config_path = Path(path).expanduser().resolve()
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ConfigError(f"unable to load configuration {config_path}: {error}") from error

    if not isinstance(raw, dict):
        raise ConfigError("configuration root must be a mapping")

    _validate(raw)
    frozen = _freeze(raw)
    return LoadedConfig(path=config_path, data=frozen, digest=config_digest(frozen))
