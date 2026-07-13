"""آموزش ensemble (XGBoost + RandomForest)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier, VotingClassifier

from barekat_genomics.ml.dataset import augment_dataset, build_labeled_dataset
from barekat_genomics.ml.evaluation import EvaluationMetrics, evaluate_holdout
from barekat_genomics.ml.features import FEATURE_NAMES
from barekat_genomics.ml.registry import ModelRegistry

try:
    from xgboost import XGBClassifier

    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    from sklearn.ensemble import GradientBoostingClassifier


def build_ensemble_model() -> object:
    rf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
    if HAS_XGBOOST:
        xgb = XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            random_state=42,
        )
        return VotingClassifier(
            estimators=[("xgb", xgb), ("rf", rf)],
            voting="soft",
            weights=[2, 1],
        )
    gb = GradientBoostingClassifier(random_state=42)
    return VotingClassifier(estimators=[("gb", gb), ("rf", rf)], voting="soft", weights=[2, 1])


def train_variant_classifier(
    knowledge_dir: Path,
    *,
    model_dir: Path,
    version: str = "v1",
    promote: bool = False,
    augment: bool = True,
) -> tuple[object, EvaluationMetrics, ModelRegistry]:
    X, y, _ = build_labeled_dataset(knowledge_dir)
    if augment:
        X, y = augment_dataset(X, y)

    model = build_ensemble_model()
    metrics, trained = evaluate_holdout(model, X, y)

    algorithm = "xgboost+rf_ensemble" if HAS_XGBOOST else "gb+rf_ensemble"
    model_file = f"variant_classifier_{version}.pkl"

    import pickle

    model_dir.mkdir(parents=True, exist_ok=True)
    out_path = model_dir / model_file
    with open(out_path, "wb") as f:
        pickle.dump(trained, f)

    registry = ModelRegistry.load(model_dir / "registry.json")
    registry.register_version(
        version,
        model_file,
        algorithm,
        FEATURE_NAMES,
        metrics.to_dict(),
        promote=promote,
    )
    registry.save(model_dir / "registry.json")
    return trained, metrics, registry
