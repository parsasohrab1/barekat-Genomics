"""تست مدیریت مرجع GRCh38 — install محلی، validation، manifest، MinIO bucket جدا."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from barekat_genomics.core.config import get_settings
from barekat_genomics.pipeline.reference import (
    BWA_MEM2_SUFFIXES,
    ensure_reference_layout,
    install_reference_from_local,
    validate_reference_bundle,
    write_reference_manifest,
)


def _make_source_tree(src: Path, build: str = "GRCh38") -> Path:
    src.mkdir(parents=True, exist_ok=True)
    (src / "known-sites").mkdir(exist_ok=True)
    fasta = src / f"{build}.fa"
    fasta.write_text(
        f">chr1 {build} primary\n"
        "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT\n",
        encoding="utf-8",
    )
    (src / f"{build}.fa.fai").write_text("chr1\t64\t20\t64\t65\n", encoding="utf-8")
    (src / f"{build}.dict").write_text(
        f"@HD\tVN:1.6\n@SQ\tSN:chr1\tLN:64\tAS:{build}\n",
        encoding="utf-8",
    )
    for sfx in BWA_MEM2_SUFFIXES:
        (src / f"{build}{sfx}").write_bytes(b"IDX" + sfx.encode())
    (src / "known-sites" / "dbsnp.vcf.gz").write_bytes(b"##fileformat=VCFv4.2\n")
    return src


@pytest.fixture()
def ref_env(tmp_path, monkeypatch):
    src = _make_source_tree(tmp_path / "source")
    dest = tmp_path / "REFERENCE_DIR"
    monkeypatch.setenv("REFERENCE_DIR", str(dest))
    monkeypatch.setenv("REF_FASTA", str(dest / "GRCh38.fa"))
    monkeypatch.setenv("BWA_INDEX_PREFIX", str(dest / "GRCh38"))
    monkeypatch.setenv("GENOME_BUILD", "GRCh38")
    monkeypatch.setenv("GENOME_VERSION", "GRCh38.p14")
    monkeypatch.setenv("DBSNP_PATH", str(dest / "known-sites" / "dbsnp.vcf.gz"))
    monkeypatch.setenv("KNOWN_SITES_VCF", str(dest / "known-sites" / "dbsnp.vcf.gz"))
    monkeypatch.setenv("REFERENCE_REQUIRE_DICT", "true")
    monkeypatch.setenv("REFERENCE_REQUIRE_KNOWN_SITES", "false")
    monkeypatch.setenv("S3_REFERENCE_BUCKET", "barekat-genomics-reference")
    get_settings.cache_clear()
    yield {"src": src, "dest": dest}
    get_settings.cache_clear()


def test_ensure_layout_creates_dirs(ref_env):
    path = ensure_reference_layout()
    assert path == ref_env["dest"]
    assert (path / "known-sites").is_dir()
    assert (path / "clinvar").is_dir()


def test_install_local_produces_valid_reference(ref_env):
    result = install_reference_from_local(ref_env["src"], genome_version="GRCh38.p14")
    assert Path(result["fasta"]).is_file()
    assert (ref_env["dest"] / "GRCh38.fa.fai").is_file()
    assert (ref_env["dest"] / "GRCh38.dict").is_file()
    assert (ref_env["dest"] / "GRCh38.amb").is_file()
    assert (ref_env["dest"] / "GRCh38.bwt.2bit.64").is_file()
    assert (ref_env["dest"] / "known-sites" / "dbsnp.vcf.gz").is_file()
    assert (ref_env["dest"] / "reference_manifest.json").is_file()

    validation = result["validation"]
    assert validation["overall"] == "PASS"
    assert validation["ready"] is True
    assert validation["minio_bucket"] == "barekat-genomics-reference"
    assert "genomes/GRCh38" in validation["minio_prefix"]


def test_validation_checklist_pass_fail(ref_env):
    before = validate_reference_bundle()
    assert before.overall == "FAIL"
    assert before.ready is False
    assert any((not c.ok and c.required) for c in before.checks)

    install_reference_from_local(ref_env["src"])
    after = validate_reference_bundle()
    assert after.overall == "PASS"
    statuses = {c.name: c.to_dict()["status"] for c in after.checks}
    assert statuses["ref_fasta"] == "PASS"
    assert statuses["fasta_index"] == "PASS"
    assert statuses["sequence_dict"] == "PASS"
    assert statuses["bwa.amb"] == "PASS"
    assert statuses["bwa_bwt"] == "PASS"
    assert "checksum:ref_fasta" in statuses


def test_manifest_checksum_detects_tamper(ref_env):
    install_reference_from_local(ref_env["src"])
    fasta = ref_env["dest"] / "GRCh38.fa"
    fasta.write_text(fasta.read_text(encoding="utf-8") + "N\n", encoding="utf-8")
    result = validate_reference_bundle()
    checksum_fails = [c for c in result.checks if c.name.startswith("checksum:") and not c.ok]
    assert checksum_fails, "باید mismatch checksum را گزارش کند"


def test_write_manifest_explicit(ref_env):
    install_reference_from_local(ref_env["src"])
    manifest = write_reference_manifest(genome_version="GRCh38.p14-test")
    assert manifest["genome_version"] == "GRCh38.p14-test"
    data = json.loads((ref_env["dest"] / "reference_manifest.json").read_text(encoding="utf-8"))
    assert "ref_fasta" in data["files"]
    assert "sha256" in data["files"]["ref_fasta"]


def test_reference_status_api_includes_bucket(client, ref_env, monkeypatch):
    install_reference_from_local(ref_env["src"])
    # client fixture از قبل ساخته شده؛ cache را برای درخواست بعدی تازه کنید
    get_settings.cache_clear()
    resp = client.get("/api/v1/pipeline/reference/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "overall" in body
    assert "minio_bucket" in body
    assert body["minio_bucket"] == "barekat-genomics-reference"
