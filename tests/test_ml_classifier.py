"""Tests for ML variant classifier pipeline."""

import json
from pathlib import Path

import pytest

from barekat_genomics.ml.classifier import VariantClassifier
from barekat_genomics.ml.dataset import build_labeled_dataset
from barekat_genomics.ml.evaluation import evaluate_holdout
from barekat_genomics.ml.features import FEATURE_NAMES, extract_features
from barekat_genomics.ml.registry import ModelRegistry
from barekat_genomics.ml.training import build_ensemble_model, train_variant_classifier
from barekat_genomics.pipeline.variant_calling import CalledVariant

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "data" / "reference" / "knowledge"
MODEL_DIR = Path(__file__).resolve().parents[1] / "data" / "models" / "test_run"


@pytest.fixture(scope="module")
def trained_model(tmp_path_factory):
    model_dir = tmp_path_factory.mktemp("models")
    trained, metrics, registry = train_variant_classifier(
        KNOWLEDGE_DIR,
        model_dir=model_dir,
        version="v1",
        promote=True,
        augment=True,
    )
    return trained, metrics, registry, model_dir


class TestFeatureEngineering:
    def test_feature_count(self):
        v = CalledVariant("chr10", 96521657, "C", "T", "SNP", 98.0, 40, "rs4244285")
        fv = extract_features(v, "CYP2C19")
        assert len(fv.to_list()) == len(FEATURE_NAMES)
        assert len(FEATURE_NAMES) == 12

    def test_cadd_sift_in_features(self):
        from barekat_genomics.knowledge.models import VariantKnowledge

        kb = VariantKnowledge(cadd_phred=20.0, sift_score=0.01, polyphen_score=0.9, phylop_score=5.0)
        v = CalledVariant("chr10", 1, "C", "T", "SNP", 90.0, 30, "rs1")
        fv = extract_features(v, "CYP2C19", kb)
        assert fv.values[6] > 0.4  # cadd_norm
        assert fv.values[7] > 0.9  # sift deleterious


class TestDataset:
    def test_labeled_dataset_has_both_classes(self):
        X, y, ids = build_labeled_dataset(KNOWLEDGE_DIR)
        assert len(ids) >= 5
        assert set(y.tolist()) == {0, 1}


class TestTraining:
    def test_holdout_metrics(self, trained_model):
        trained, metrics, registry, _ = trained_model
        assert metrics.precision >= 0.5
        assert metrics.recall >= 0.5
        assert registry.production_version == "v1"
        assert "v1" in registry.versions

    def test_registry_ab_routing(self, trained_model):
        _, _, registry, _ = trained_model
        registry.ab_test.enabled = True
        registry.ab_test.challenger_version = "v1"
        registry.ab_test.traffic_pct = 0.5
        versions = {registry.route_version(f"key-{i}") for i in range(100)}
        assert "v1" in versions


class TestClassifier:
    def test_predict_returns_version(self, trained_model, monkeypatch):
        _, _, registry, model_dir = trained_model
        monkeypatch.setenv("MODEL_PATH", str(model_dir))
        from barekat_genomics.core.config import get_settings

        get_settings.cache_clear()
        clf = VariantClassifier()
        v = CalledVariant("chr10", 96521657, "C", "T", "SNP", 98.0, 40, "rs4244285")
        score, conf, ver = clf.predict_from_variant(v, "CYP2C19", routing_key="rs4244285")
        assert 0.0 <= score <= 1.0
        assert 0.0 <= conf <= 1.0
        assert ver == "v1"
        get_settings.cache_clear()

    def test_evaluation_precision_recall(self):
        X, y, _ = build_labeled_dataset(KNOWLEDGE_DIR)
        model = build_ensemble_model()
        metrics, _ = evaluate_holdout(model, X, y, test_size=0.3)
        assert 0.0 <= metrics.precision <= 1.0
        assert 0.0 <= metrics.recall <= 1.0
