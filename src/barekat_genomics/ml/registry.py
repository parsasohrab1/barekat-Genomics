"""نسخه‌بندی مدل و A/B test در production."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from barekat_genomics.core.config import get_settings


@dataclass
class ModelVersionInfo:
    version: str
    file: str
    algorithm: str
    features: list[str]
    metrics: dict
    created_at: str
    status: str = "staging"


@dataclass
class ABTestConfig:
    enabled: bool = False
    challenger_version: str = ""
    traffic_pct: float = 0.1


@dataclass
class ModelRegistry:
    production_version: str = "v1"
    versions: dict[str, ModelVersionInfo] = field(default_factory=dict)
    ab_test: ABTestConfig = field(default_factory=ABTestConfig)

    @classmethod
    def load(cls, path: Path | None = None) -> ModelRegistry:
        settings = get_settings()
        registry_path = path or (Path(settings.model_path) / "registry.json")
        if not registry_path.is_file():
            return cls()
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        versions = {
            k: ModelVersionInfo(**v) for k, v in data.get("versions", {}).items()
        }
        ab = data.get("ab_test", {})
        return cls(
            production_version=data.get("production_version", "v1"),
            versions=versions,
            ab_test=ABTestConfig(
                enabled=ab.get("enabled", False),
                challenger_version=ab.get("challenger_version", ""),
                traffic_pct=float(ab.get("traffic_pct", 0.1)),
            ),
        )

    def save(self, path: Path | None = None) -> None:
        settings = get_settings()
        registry_path = path or (Path(settings.model_path) / "registry.json")
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "production_version": self.production_version,
            "versions": {k: v.__dict__ for k, v in self.versions.items()},
            "ab_test": self.ab_test.__dict__,
        }
        registry_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def route_version(self, routing_key: str | None) -> str:
        """انتخاب نسخه مدل برای A/B test."""
        if not self.ab_test.enabled or not self.ab_test.challenger_version:
            return self.production_version
        if not routing_key:
            return self.production_version
        bucket = int(hashlib.md5(routing_key.encode()).hexdigest(), 16) % 100
        if bucket < int(self.ab_test.traffic_pct * 100):
            return self.ab_test.challenger_version
        return self.production_version

    def model_file(self, version: str) -> str:
        if version in self.versions:
            return self.versions[version].file
        settings = get_settings()
        return settings.variant_classifier_model

    def register_version(
        self,
        version: str,
        file: str,
        algorithm: str,
        features: list[str],
        metrics: dict,
        *,
        promote: bool = False,
    ) -> None:
        self.versions[version] = ModelVersionInfo(
            version=version,
            file=file,
            algorithm=algorithm,
            features=features,
            metrics=metrics,
            created_at=datetime.now(timezone.utc).isoformat(),
            status="production" if promote else "staging",
        )
        if promote:
            self.production_version = version
