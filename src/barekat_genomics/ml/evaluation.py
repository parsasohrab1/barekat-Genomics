"""ارزیابی مدل: precision/recall روی hold-out."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split


@dataclass
class EvaluationMetrics:
    precision: float
    recall: float
    f1: float
    accuracy: float
    roc_auc: float | None
    holdout_size: int
    train_size: int

    def to_dict(self) -> dict:
        return {
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "accuracy": round(self.accuracy, 4),
            "roc_auc": round(self.roc_auc, 4) if self.roc_auc is not None else None,
            "holdout_size": self.holdout_size,
            "train_size": self.train_size,
        }


def evaluate_holdout(
    model,
    X: np.ndarray,
    y: np.ndarray,
    *,
    test_size: float = 0.25,
    random_state: int = 42,
) -> tuple[EvaluationMetrics, object]:
    """تقسیم hold-out و محاسبه precision/recall."""
    stratify = y if len(np.unique(y)) > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=stratify
    )

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    roc = None
    if hasattr(model, "predict_proba") and len(np.unique(y_test)) > 1:
        try:
            proba = model.predict_proba(X_test)[:, 1]
            roc = float(roc_auc_score(y_test, proba))
        except ValueError:
            roc = None

    metrics = EvaluationMetrics(
        precision=float(precision_score(y_test, y_pred, zero_division=0)),
        recall=float(recall_score(y_test, y_pred, zero_division=0)),
        f1=float(f1_score(y_test, y_pred, zero_division=0)),
        accuracy=float(accuracy_score(y_test, y_pred)),
        roc_auc=roc,
        holdout_size=len(y_test),
        train_size=len(y_train),
    )
    return metrics, model
