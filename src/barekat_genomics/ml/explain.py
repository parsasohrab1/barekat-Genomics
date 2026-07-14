"""Explainability: SHAP در صورت نصب، در غیر این صورت feature_importances_ / permutation."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from barekat_genomics.ml.features import FEATURE_NAMES


def _iter_estimators(model) -> list[tuple[str, object]]:
    if hasattr(model, "named_estimators_"):
        return list(model.named_estimators_.items())
    if hasattr(model, "estimators_"):
        # VotingClassifier before named_estimators_ in some versions
        names = [n for n, _ in getattr(model, "estimators", [])] or [
            f"est{i}" for i in range(len(model.estimators_))
        ]
        return list(zip(names, model.estimators_))
    return [("model", model)]


def extract_native_importance(model) -> dict[str, float]:
    """استخراج اهمیت ویژگی از اعضای درخت‌محور ensemble."""
    agg = np.zeros(len(FEATURE_NAMES), dtype=float)
    count = 0
    for _name, est in _iter_estimators(model):
        if hasattr(est, "feature_importances_"):
            imp = np.asarray(est.feature_importances_, dtype=float)
            if imp.shape[0] == len(FEATURE_NAMES):
                agg += imp
                count += 1
    if count == 0:
        return {name: 0.0 for name in FEATURE_NAMES}
    agg = agg / count
    total = float(agg.sum()) or 1.0
    return {name: float(v / total) for name, v in zip(FEATURE_NAMES, agg)}


def permutation_importance_map(model, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
    from sklearn.inspection import permutation_importance

    result = permutation_importance(model, X, y, n_repeats=5, random_state=42, scoring="f1")
    imp = np.maximum(result.importances_mean, 0.0)
    total = float(imp.sum()) or 1.0
    return {name: float(v / total) for name, v in zip(FEATURE_NAMES, imp)}


def shap_contributions(model, feature_vector: list[float]) -> dict[str, float] | None:
    """سعی در محاسبه SHAP؛ بدون وابستگی اجباری."""
    try:
        import shap
    except ImportError:
        return None

    X = np.asarray(feature_vector, dtype=float).reshape(1, -1)
    tree_est = None
    for _name, est in _iter_estimators(model):
        cls = type(est).__name__.lower()
        if "forest" in cls or "xgb" in cls or "boost" in cls or "histogram" in cls:
            tree_est = est
            break
    if tree_est is None:
        return None
    try:
        explainer = shap.TreeExplainer(tree_est)
        values = explainer.shap_values(X)
        if isinstance(values, list):
            values = values[1] if len(values) > 1 else values[0]
        row = np.asarray(values).reshape(-1)
        if row.shape[0] != len(FEATURE_NAMES):
            return None
        abs_sum = float(np.abs(row).sum()) or 1.0
        return {name: float(v / abs_sum) for name, v in zip(FEATURE_NAMES, row)}
    except Exception:
        return None


def explain_prediction(
    model,
    feature_vector: list[float],
    *,
    global_importance: dict[str, float] | None = None,
    top_k: int = 5,
) -> dict:
    """
    توضیح تصمیم مدل برای یک نمونه.
    اولویت: SHAP → مشارکت وزن‌دار ویژگی × اهمیت سراسری → اهمیت سراسری.
    """
    shap_vals = shap_contributions(model, feature_vector)
    method = "shap" if shap_vals else "feature_importance"
    contrib = shap_vals
    if contrib is None:
        base = global_importance or extract_native_importance(model)
        # وزن‌دهی با مقدار ویژگی برای تفسیر محلی ساده
        local = {
            name: float(base.get(name, 0.0) * (0.35 + 0.65 * float(feature_vector[i])))
            for i, name in enumerate(FEATURE_NAMES)
        }
        total = sum(abs(v) for v in local.values()) or 1.0
        contrib = {k: v / total for k, v in local.items()}
        method = "weighted_importance"

    ranked = sorted(contrib.items(), key=lambda kv: abs(kv[1]), reverse=True)
    top = [{"feature": k, "contribution": round(v, 4)} for k, v in ranked[:top_k]]
    return {
        "method": method,
        "top_features": top,
        "contributions": {k: round(v, 4) for k, v in contrib.items()},
    }


def compute_and_persist_importance(
    model,
    X: np.ndarray,
    y: np.ndarray,
    model_dir: Path,
    version: str,
) -> dict:
    native = extract_native_importance(model)
    try:
        perm = permutation_importance_map(model, X[: min(len(X), 400)], y[: min(len(y), 400)])
    except Exception:
        perm = native

    # میانگین native و permutation
    blended = {
        name: round(0.5 * native.get(name, 0.0) + 0.5 * perm.get(name, 0.0), 4)
        for name in FEATURE_NAMES
    }
    ranked = sorted(blended.items(), key=lambda kv: kv[1], reverse=True)
    payload = {
        "version": version,
        "method": "native+permutation",
        "importance": blended,
        "top_features": [{"feature": k, "importance": v} for k, v in ranked[:8]],
    }
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / f"feature_importance_{version}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_global_importance(model_dir: Path, version: str) -> dict[str, float] | None:
    path = model_dir / f"feature_importance_{version}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("importance") or None
