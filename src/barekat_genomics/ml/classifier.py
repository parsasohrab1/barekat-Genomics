"""مدل ML برای طبقه‌بندی واریانت — نسخه‌بندی + A/B test."""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

from barekat_genomics.core.config import get_settings
from barekat_genomics.ml.features import FEATURE_NAMES, FeatureVector, extract_features
from barekat_genomics.ml.registry import ModelRegistry
from barekat_genomics.ml.training import train_variant_classifier


class VariantClassifier:
    """طبقه‌بند واریانت با ensemble و مسیریابی A/B."""

    def __init__(self) -> None:
        settings = get_settings()
        self.model_dir = Path(settings.model_path)
        self.registry = ModelRegistry.load(self.model_dir / "registry.json")
        if settings.ml_ab_test_enabled:
            self.registry.ab_test.enabled = True
            self.registry.ab_test.challenger_version = settings.ml_ab_test_challenger
            self.registry.ab_test.traffic_pct = settings.ml_ab_test_traffic_pct
        self._models: dict[str, object] = {}
        self._ensure_models_loaded()

    def _ensure_models_loaded(self) -> None:
        versions = {self.registry.production_version}
        if self.registry.ab_test.enabled and self.registry.ab_test.challenger_version:
            versions.add(self.registry.ab_test.challenger_version)

        for ver in versions:
            if ver in self._models:
                continue
            path = self.model_dir / self.registry.model_file(ver)
            if path.is_file():
                with open(path, "rb") as f:
                    self._models[ver] = pickle.load(f)
            elif ver == self.registry.production_version:
                self._train_bootstrap_model(ver)

    def _train_bootstrap_model(self, version: str) -> None:
        """آموزش اولیه از ClinVar+PharmGKB اگر مدل وجود ندارد."""
        knowledge_dir = Path(get_settings().knowledge_dir) if get_settings().knowledge_dir else (
            Path(__file__).resolve().parents[3] / "data" / "reference" / "knowledge"
        )
        trained, metrics, registry = train_variant_classifier(
            knowledge_dir,
            model_dir=self.model_dir,
            version=version,
            promote=True,
            augment=True,
        )
        self.registry = registry
        self._models[version] = trained
        _ = metrics

    def predict(
        self,
        features: list[float] | FeatureVector,
        *,
        routing_key: str | None = None,
    ) -> tuple[float, float, str]:
        """
        پیش‌بینی اهمیت واریانت.
        بازگشت: (score, confidence, model_version)
        """
        if isinstance(features, FeatureVector):
            vec = features.to_list()
        else:
            vec = features

        version = self.registry.route_version(routing_key)
        if version not in self._models:
            self._ensure_models_loaded()
        model = self._models.get(version) or self._models.get(self.registry.production_version)
        if model is None:
            raise RuntimeError("مدل طبقه‌بندی واریانت بارگذاری نشد")

        X = np.array(vec, dtype=np.float32).reshape(1, -1)
        proba = model.predict_proba(X)[0]
        score = float(proba[1]) if len(proba) > 1 else float(proba[0])
        confidence = float(max(proba))
        return score, confidence, version

    def predict_from_variant(self, variant, gene: str | None, kb=None, routing_key: str | None = None):
        fv = extract_features(variant, gene, kb)
        return self.predict(fv, routing_key=routing_key or variant.rs_id)

    def save(self, path: str | Path, version: str = "v1") -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        model = self._models.get(version)
        if model is None:
            raise ValueError(f"نسخه {version} بارگذاری نشده")
        with open(path, "wb") as f:
            pickle.dump(model, f)

    @property
    def feature_names(self) -> list[str]:
        return FEATURE_NAMES

    @property
    def active_version(self) -> str:
        return self.registry.production_version
