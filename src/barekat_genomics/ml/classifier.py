"""مدل ML برای طبقه‌بندی و اولویت‌بندی واریانت‌ها."""

import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from barekat_genomics.core.config import get_settings


class VariantClassifier:
    """طبقه‌بند واریانت‌ها بر اساس اهمیت بالینی."""

    def __init__(self) -> None:
        self.model: RandomForestClassifier | None = None
        self._load_or_train()

    def _load_or_train(self) -> None:
        settings = get_settings()
        model_path = Path(settings.model_path) / settings.variant_classifier_model

        if model_path.exists():
            with open(model_path, "rb") as f:
                self.model = pickle.load(f)
        else:
            self.model = self._train_default_model()

    def _train_default_model(self) -> RandomForestClassifier:
        """آموزش مدل پیش‌فرض با داده‌های شبیه‌سازی‌شده."""
        rng = np.random.RandomState(42)
        n = 500
        X = rng.rand(n, 5)
        y = (X[:, 0] * 0.4 + X[:, 3] * 0.3 + X[:, 4] * 0.2 + rng.rand(n) * 0.1 > 0.5).astype(int)

        model = RandomForestClassifier(n_estimators=50, random_state=42)
        model.fit(X, y)
        return model

    def predict(self, features: list[float]) -> tuple[float, float]:
        """پیش‌بینی اهمیت واریانت. بازگشت: (score, confidence)."""
        X = np.array(features).reshape(1, -1)
        proba = self.model.predict_proba(X)[0]
        score = float(proba[1]) if len(proba) > 1 else float(proba[0])
        confidence = float(max(proba))
        return score, confidence

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
