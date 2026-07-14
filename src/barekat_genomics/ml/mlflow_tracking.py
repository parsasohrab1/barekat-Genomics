"""ردیابی اختیاری MLflow برای آموزش مدل."""

from __future__ import annotations

from pathlib import Path


def log_training_run(
    *,
    version: str,
    algorithm: str,
    metrics: dict,
    model_path: Path,
    params: dict | None = None,
) -> dict:
    """
    اگر mlflow نصب باشد run را ثبت می‌کند؛ در غیر این صورت no-op امن.
    """
    try:
        import mlflow
        import mlflow.sklearn
    except ImportError:
        return {"logged": False, "reason": "mlflow_not_installed"}

    experiment = "barekat-variant-classifier"
    mlflow.set_experiment(experiment)
    with mlflow.start_run(run_name=f"variant-classifier-{version}"):
        mlflow.log_param("version", version)
        mlflow.log_param("algorithm", algorithm)
        for k, v in (params or {}).items():
            mlflow.log_param(k, v)
        for k, v in metrics.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                mlflow.log_metric(k, float(v))
        if model_path.is_file():
            mlflow.log_artifact(str(model_path))
            importance = model_path.parent / f"feature_importance_{version}.json"
            if importance.is_file():
                mlflow.log_artifact(str(importance))
        return {"logged": True, "experiment": experiment, "version": version}
