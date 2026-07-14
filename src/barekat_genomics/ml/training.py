"""آموزش ensemble پیشرفته (HistGB / XGB / RF / MLP) با مقایسه baseline."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    RandomForestClassifier,
    VotingClassifier,
)
from sklearn.neural_network import MLPClassifier

from barekat_genomics.ml.dataset import (
    augment_dataset,
    build_labeled_dataset,
    load_anonymized_training,
)
from barekat_genomics.ml.evaluation import EvaluationMetrics, evaluate_holdout
from barekat_genomics.ml.explain import compute_and_persist_importance
from barekat_genomics.ml.features import FEATURE_NAMES
from barekat_genomics.ml.registry import ModelRegistry

try:
    from xgboost import XGBClassifier

    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False


def build_baseline_rf() -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight="balanced",
    )


def build_ensemble_model(*, deep_tabular: bool = True) -> object:
    """
    Ensemble نسخه v2:
    - HistGradientBoosting (tabular مدرن)
    - RandomForest
    - XGBoost در صورت نصب
    - MLP به‌عنوان لایه deep tabular (اختیاری)
    """
    rf = build_baseline_rf()
    hist = HistGradientBoostingClassifier(
        max_depth=6,
        learning_rate=0.08,
        max_iter=150,
        random_state=42,
    )
    estimators: list[tuple[str, object]] = [("histgb", hist), ("rf", rf)]
    weights = [2, 1]

    if HAS_XGBOOST:
        xgb = XGBClassifier(
            n_estimators=120,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            random_state=42,
        )
        estimators.insert(0, ("xgb", xgb))
        weights = [2, 2, 1]

    if deep_tabular:
        # early_stopping روی دیتاست‌های کوچک دانش بالینی (hold-out) می‌شکند
        mlp = MLPClassifier(
            hidden_layer_sizes=(64, 32),
            activation="relu",
            max_iter=400,
            early_stopping=False,
            random_state=42,
        )
        estimators.append(("mlp", mlp))
        weights.append(1)

    return VotingClassifier(estimators=estimators, voting="soft", weights=weights)


def _algorithm_tag(*, deep_tabular: bool) -> str:
    parts = []
    if HAS_XGBOOST:
        parts.append("xgb")
    parts.append("histgb")
    parts.append("rf")
    if deep_tabular:
        parts.append("mlp")
    return "+".join(parts) + "_ensemble"


def train_variant_classifier(
    knowledge_dir: Path,
    *,
    model_dir: Path,
    version: str = "v1",
    promote: bool = False,
    augment: bool = True,
    training_csv: Path | None = None,
    fine_tune: bool = False,
    deep_tabular: bool = True,
    compare_baseline: bool = True,
    log_mlflow: bool = False,
) -> tuple[object, EvaluationMetrics, ModelRegistry]:
    X, y, _ids = build_labeled_dataset(knowledge_dir)

    if training_csv and Path(training_csv).is_file():
        X_anon, y_anon, _ = load_anonymized_training(Path(training_csv))
        if fine_tune:
            # fine-tune محدود: تکرار کمتر داده ناشناس برای تطبیق خفیف
            X = np.vstack([X, X_anon, X_anon[: max(1, len(X_anon) // 3)]])
            y = np.concatenate([y, y_anon, y_anon[: max(1, len(y_anon) // 3)]])
        else:
            X = np.vstack([X, X_anon])
            y = np.concatenate([y, y_anon])

    if augment:
        X, y = augment_dataset(X, y)

    baseline_metrics = None
    if compare_baseline:
        baseline = build_baseline_rf()
        baseline_metrics, _ = evaluate_holdout(baseline, X, y)

    model = build_ensemble_model(deep_tabular=deep_tabular)
    metrics, trained = evaluate_holdout(model, X, y)

    delta = {}
    if baseline_metrics is not None:
        delta = {
            "baseline_algorithm": "random_forest",
            "baseline_f1": baseline_metrics.f1,
            "baseline_accuracy": baseline_metrics.accuracy,
            "delta_f1": round(metrics.f1 - baseline_metrics.f1, 4),
            "delta_accuracy": round(metrics.accuracy - baseline_metrics.accuracy, 4),
            "improved_vs_baseline": metrics.f1 >= baseline_metrics.f1,
        }

    algorithm = _algorithm_tag(deep_tabular=deep_tabular)
    model_file = f"variant_classifier_{version}.pkl"

    import pickle

    model_dir.mkdir(parents=True, exist_ok=True)
    out_path = model_dir / model_file
    with open(out_path, "wb") as f:
        pickle.dump(trained, f)

    importance = compute_and_persist_importance(trained, X, y, model_dir, version)

    metrics_payload = metrics.to_dict()
    metrics_payload.update(delta)
    metrics_payload["feature_importance_top"] = importance.get("top_features", [])[:5]
    metrics_payload["training_csv"] = str(training_csv) if training_csv else None
    metrics_payload["fine_tune"] = fine_tune

    registry = ModelRegistry.load(model_dir / "registry.json")
    registry.register_version(
        version,
        model_file,
        algorithm,
        FEATURE_NAMES,
        metrics_payload,
        promote=promote,
    )
    registry.save(model_dir / "registry.json")

    if log_mlflow:
        from barekat_genomics.ml.mlflow_tracking import log_training_run

        log_training_run(
            version=version,
            algorithm=algorithm,
            metrics=metrics_payload,
            model_path=out_path,
            params={
                "deep_tabular": deep_tabular,
                "fine_tune": fine_tune,
                "augment": augment,
                "training_csv": str(training_csv) if training_csv else "",
            },
        )

    summary_path = model_dir / f"train_summary_{version}.json"
    summary_path.write_text(
        json.dumps(
            {
                "version": version,
                "algorithm": algorithm,
                "metrics": metrics_payload,
                "promoted": promote,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return trained, metrics, registry
