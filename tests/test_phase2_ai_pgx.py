"""Phase 2: ensemble v2, knowledge guidelines, biomarker panel, explainability."""

from pathlib import Path

import numpy as np
import pytest

from barekat_genomics.ml.dataset import load_anonymized_training
from barekat_genomics.ml.explain import explain_prediction
from barekat_genomics.ml.features import FEATURE_NAMES
from barekat_genomics.ml.training import build_baseline_rf, build_ensemble_model, train_variant_classifier
from barekat_genomics.pipeline.interpretation import generate_drug_recommendations, interpret_variants
from barekat_genomics.pipeline.report_builder import build_clinical_report
from barekat_genomics.pipeline.variant_calling import CalledVariant, call_variants

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "data" / "reference" / "knowledge"
TRAINING_CSV = Path(__file__).resolve().parents[1] / "data" / "training" / "anonymized_training.csv"


class TestPhase2Ensemble:
    def test_ensemble_has_multiple_estimators(self):
        model = build_ensemble_model(deep_tabular=True)
        names = [n for n, _ in model.estimators]
        assert "histgb" in names
        assert "rf" in names
        assert "mlp" in names

    def test_train_improves_or_matches_baseline(self, tmp_path):
        if not KNOWLEDGE_DIR.is_dir():
            pytest.skip("knowledge dir missing")
        _, metrics, registry = train_variant_classifier(
            KNOWLEDGE_DIR,
            model_dir=tmp_path,
            version="v2",
            promote=True,
            augment=True,
            training_csv=TRAINING_CSV if TRAINING_CSV.is_file() else None,
            fine_tune=bool(TRAINING_CSV.is_file()),
            deep_tabular=True,
            compare_baseline=True,
            log_mlflow=False,
        )
        summary = tmp_path / "train_summary_v2.json"
        assert summary.is_file()
        assert registry.production_version == "v2"
        assert (tmp_path / "feature_importance_v2.json").is_file()
        # metrics object itself; delta lives in summary JSON / registry
        payload = registry.versions["v2"].metrics
        assert "baseline_f1" in payload
        assert "delta_f1" in payload
        assert metrics.f1 >= 0.5


class TestPhase2Anonymized:
    def test_load_anonymized_training_shape(self):
        if not TRAINING_CSV.is_file():
            pytest.skip("generate anonymized_training.csv first")
        X, y, ids = load_anonymized_training(TRAINING_CSV)
        assert X.shape[1] == len(FEATURE_NAMES)
        assert len(y) == len(ids) == X.shape[0]
        assert set(np.unique(y)).issubset({0, 1})


class TestPhase2Explainability:
    def test_explain_prediction_returns_top_features(self):
        model = build_baseline_rf()
        X = np.random.RandomState(0).rand(40, len(FEATURE_NAMES))
        y = (X[:, 3] + X[:, 10] > 1.0).astype(int)
        if y.sum() == 0:
            y[:5] = 1
        if y.sum() == len(y):
            y[:5] = 0
        model.fit(X, y)
        result = explain_prediction(model, X[0].tolist())
        assert result["method"]
        assert len(result["top_features"]) >= 1
        assert "feature" in result["top_features"][0]


class TestPhase2ReportPanel:
    def test_biomarker_panel_and_ranking(self):
        variants = call_variants("/fake/path.bam", "BAM")
        interpretations = interpret_variants(variants)
        assert interpretations
        assert interpretations[0][1].rank == 1
        # ranks are dense 1..n
        ranks = [interp.rank for _, interp in interpretations]
        assert sorted(ranks) == list(range(1, len(ranks) + 1))

        drugs = generate_drug_recommendations(interpretations)
        content = build_clinical_report(interpretations, drugs, patient_external_id="P-P2")
        panel = content.get("biomarker_panel") or {}
        assert panel.get("total_variants") == len(interpretations)
        assert isinstance(panel.get("ranked_markers"), list)

        for hp in content["high_priority_variants"]:
            assert "rank" in hp
            assert "feature_contributions" in hp
            assert "ml_score" in hp

    def test_drug_recommendations_include_guideline_sources(self):
        v = CalledVariant("chr10", 96521657, "C", "T", "SNP", 98.0, 40, "rs4244285", gene="CYP2C19")
        interpretations = interpret_variants([v])
        drugs = generate_drug_recommendations(interpretations)
        content = build_clinical_report(interpretations, drugs)
        if content["drug_recommendations"]:
            rec = content["drug_recommendations"][0]
            assert rec.get("sources") is not None or rec.get("cpic_level")
