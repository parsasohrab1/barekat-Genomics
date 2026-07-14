"""مسیرهای مرجع ژنوم GRCh38، اعتبارسنجی Pass/Fail، و همگام‌سازی با MinIO."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from barekat_genomics.core.config import get_settings

REFERENCE_PREFIX = "genomes"
MANIFEST_NAME = "reference_manifest.json"

# پسوندهای ایندکس BWA-MEM2 و BWA کلاسیک
BWA_MEM2_SUFFIXES = (".amb", ".ann", ".bwt.2bit.64", ".pac", ".0123")
BWA_CLASSIC_SUFFIXES = (".amb", ".ann", ".bwt", ".pac", ".sa")


@dataclass
class ReferenceCheck:
    name: str
    path: str
    ok: bool
    required: bool = True
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "ok": self.ok,
            "required": self.required,
            "detail": self.detail,
            "status": "PASS" if self.ok else ("FAIL" if self.required else "WARN"),
        }


@dataclass
class ReferenceValidationResult:
    genome_build: str
    genome_version: str
    ready: bool
    overall: str  # PASS | FAIL
    checks: list[ReferenceCheck] = field(default_factory=list)
    minio_bucket: str = ""
    minio_prefix: str = ""
    reference_dir: str = ""
    manifest_path: str | None = None

    def to_dict(self) -> dict:
        return {
            "genome_build": self.genome_build,
            "genome_version": self.genome_version,
            "ready": self.ready,
            "overall": self.overall,
            "reference_dir": self.reference_dir,
            "minio_bucket": self.minio_bucket,
            "minio_prefix": self.minio_prefix,
            "manifest_path": self.manifest_path,
            "checks": [c.to_dict() for c in self.checks],
            "failed": [c.name for c in self.checks if c.required and not c.ok],
            "warnings": [c.name for c in self.checks if not c.required and not c.ok],
        }


@dataclass
class ReferenceBundle:
    genome_build: str
    genome_version: str
    reference_dir: Path
    ref_fasta: Path
    bwa_index_prefix: Path
    snpeff_db: str
    dbsnp_vcf: Path | None
    known_sites_vcf: Path | None
    clinvar_vcf: Path | None
    pharmgkb_dir: Path | None

    @property
    def fasta_index(self) -> Path:
        return Path(str(self.ref_fasta) + ".fai")

    @property
    def sequence_dict(self) -> Path:
        return self.ref_fasta.with_suffix(".dict")

    @property
    def manifest_path(self) -> Path:
        return self.reference_dir / MANIFEST_NAME

    @property
    def known_sites_dir(self) -> Path:
        return self.reference_dir / "known-sites"

    def bwa_index_files(self) -> dict[str, Path]:
        """کشف فایل‌های ایندکس BWA-MEM2 یا BWA کنار prefix."""
        found: dict[str, Path] = {}
        prefix = str(self.bwa_index_prefix)
        for suffix in BWA_MEM2_SUFFIXES + BWA_CLASSIC_SUFFIXES:
            candidate = Path(prefix + suffix)
            if candidate.is_file():
                found[suffix] = candidate
        # glob اضافی برای نام‌گذاری غیراستاندارد
        parent = self.bwa_index_prefix.parent
        stem = self.bwa_index_prefix.name
        if parent.is_dir():
            for path in parent.glob(f"{stem}*"):
                if path.is_file() and path.suffix not in {".fa", ".fasta", ".fai", ".dict"}:
                    key = path.name[len(stem) :] or path.name
                    found.setdefault(key, path)
        return found

    @property
    def has_bwa_index(self) -> bool:
        files = self.bwa_index_files()
        return ".amb" in files and (".ann" in files) and (
            ".bwt.2bit.64" in files or ".bwt" in files or any("bwt" in k for k in files)
        )

    @property
    def reference_ready(self) -> bool:
        settings = get_settings()
        ok = self.ref_fasta.is_file() and self.fasta_index.is_file() and self.has_bwa_index
        if settings.reference_require_dict:
            ok = ok and self.sequence_dict.is_file()
        return ok


def get_reference_bundle(genome_build: str | None = None) -> ReferenceBundle:
    settings = get_settings()
    build = genome_build or settings.genome_build
    ref_dir = Path(settings.reference_dir)

    ref_fasta = Path(settings.ref_fasta) if settings.ref_fasta else ref_dir / f"{build}.fa"
    if settings.bwa_index_prefix:
        bwa_prefix = Path(settings.bwa_index_prefix)
    else:
        # هم‌نام با basename فاستا داخل REFERENCE_DIR
        bwa_prefix = ref_dir / ref_fasta.stem

    known_sites = None
    if settings.known_sites_vcf:
        known_sites = Path(settings.known_sites_vcf)
    elif settings.dbsnp_path:
        dbsnp_candidate = Path(settings.dbsnp_path)
        if dbsnp_candidate.is_file():
            known_sites = dbsnp_candidate
        else:
            nested = ref_dir / "known-sites" / "dbsnp.vcf.gz"
            if nested.is_file():
                known_sites = nested

    dbsnp = Path(settings.dbsnp_path) if settings.dbsnp_path else None
    clinvar = Path(settings.clinvar_path) if settings.clinvar_path else ref_dir / "clinvar" / "clinvar.vcf.gz"
    pharmgkb = Path(settings.pharmgkb_path) if settings.pharmgkb_path else ref_dir / "pharmgkb"

    return ReferenceBundle(
        genome_build=build,
        genome_version=settings.genome_version,
        reference_dir=ref_dir,
        ref_fasta=ref_fasta,
        bwa_index_prefix=bwa_prefix,
        snpeff_db=settings.snpeff_db,
        dbsnp_vcf=dbsnp if dbsnp and dbsnp.is_file() else known_sites,
        known_sites_vcf=known_sites if known_sites and known_sites.is_file() else None,
        clinvar_vcf=clinvar if clinvar.is_file() else None,
        pharmgkb_dir=pharmgkb if pharmgkb.exists() else None,
    )


def sample_work_dir(sample_label: str) -> Path:
    settings = get_settings()
    return Path(settings.pipeline_work_dir) / sample_label


def file_sha256(path: Path, *, full: bool = False, max_bytes: int = 64 * 1024 * 1024) -> str:
    """Checksum SHA-256 — full برای فایل‌های کوچک، نمونه‌گیری برای فایل‌های بزرگ."""
    h = hashlib.sha256()
    size = path.stat().st_size
    limit = size if full or size <= max_bytes else max_bytes
    with path.open("rb") as f:
        remaining = limit
        while remaining > 0:
            chunk = f.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            h.update(chunk)
            remaining -= len(chunk)
    digest = h.hexdigest()
    if not full and size > max_bytes:
        return f"{digest}:partial:{limit}:{size}"
    return digest


def _read_fasta_header(path: Path) -> str | None:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith(">"):
                    return line[1:].strip()
    except OSError:
        return None
    return None


def _guess_build_from_header(header: str | None) -> str | None:
    if not header:
        return None
    upper = header.upper()
    if "GRCH38" in upper or "HG38" in upper or "CHR1" in upper:
        return "GRCh38"
    if "GRCH37" in upper or "HG19" in upper:
        return "GRCh37"
    return None


def ensure_reference_layout(genome_build: str | None = None) -> Path:
    """ایجاد ساختار پوشه REFERENCE_DIR."""
    refs = get_reference_bundle(genome_build)
    refs.reference_dir.mkdir(parents=True, exist_ok=True)
    (refs.reference_dir / "known-sites").mkdir(exist_ok=True)
    (refs.reference_dir / "clinvar").mkdir(exist_ok=True)
    (refs.reference_dir / "pharmgkb").mkdir(exist_ok=True)
    return refs.reference_dir


def install_reference_from_local(
    source_dir: Path | str,
    *,
    genome_build: str | None = None,
    genome_version: str | None = None,
    copy: bool = True,
) -> dict:
    """
    بارگذاری GRCh38 از مسیر محلی به REFERENCE_DIR.

    source_dir باید شامل حداقل `*.fa|*.fasta` و در صورت وجود `.fai` / `.dict` / ایندکس BWA باشد.
    """
    settings = get_settings()
    src = Path(source_dir)
    if not src.is_dir():
        raise FileNotFoundError(f"مسیر مبدأ معتبر نیست: {src}")

    refs = get_reference_bundle(genome_build)
    dest = ensure_reference_layout(refs.genome_build)
    build = refs.genome_build
    version = genome_version or settings.genome_version

    # یافتن فاستا
    fasta_candidates = list(src.glob("*.fa")) + list(src.glob("*.fasta")) + list(src.glob("*.fa.gz"))
    if not fasta_candidates:
        # یک سطح پایین‌تر
        fasta_candidates = list(src.rglob("*.fa")) + list(src.rglob("*.fasta"))
    if not fasta_candidates:
        raise FileNotFoundError(f"هیچ فایل FASTA در {src} یافت نشد")

    # ترجیح نام GRCh38*
    fasta_src = next(
        (p for p in fasta_candidates if build.lower() in p.name.lower() or "hg38" in p.name.lower()),
        fasta_candidates[0],
    )
    fasta_dest = dest / f"{build}.fa"
    _transfer(fasta_src, fasta_dest, copy=copy)

    # fai / dict هم‌نام
    for suffix, dest_name in ((".fai", f"{build}.fa.fai"), (".dict", f"{build}.dict")):
        sibling = Path(str(fasta_src) + suffix) if suffix == ".fai" else fasta_src.with_suffix(".dict")
        alt = src / dest_name
        chosen = sibling if sibling.is_file() else (alt if alt.is_file() else None)
        if chosen:
            _transfer(chosen, dest / dest_name, copy=copy)

    # ایندکس‌های BWA از مبدأ
    copied_indexes: list[str] = []
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        name = path.name
        if any(name.endswith(sfx) for sfx in BWA_MEM2_SUFFIXES + BWA_CLASSIC_SUFFIXES):
            # نرمال‌سازی به {build}{suffix}
            for sfx in BWA_MEM2_SUFFIXES + BWA_CLASSIC_SUFFIXES:
                if name.endswith(sfx):
                    target = dest / f"{build}{sfx}"
                    _transfer(path, target, copy=copy)
                    copied_indexes.append(str(target))
                    break

    # known-sites
    known_dest_dir = dest / "known-sites"
    for pattern in ("*dbsnp*.vcf*", "*known*sites*.vcf*", "*Mills*.vcf*", "*1000G*.vcf*"):
        for path in src.rglob(pattern):
            if path.is_file():
                _transfer(path, known_dest_dir / path.name, copy=copy)

    manifest = write_reference_manifest(build, genome_version=version)
    validation = validate_reference_bundle(build)
    return {
        "reference_dir": str(dest),
        "fasta": str(fasta_dest),
        "bwa_indexes": copied_indexes,
        "manifest": manifest,
        "validation": validation.to_dict(),
    }


def write_reference_manifest(
    genome_build: str | None = None,
    *,
    genome_version: str | None = None,
) -> dict:
    """ نوشتن manifest با checksum برای validation بعدی."""
    settings = get_settings()
    refs = get_reference_bundle(genome_build)
    version = genome_version or refs.genome_version or settings.genome_version
    files: dict[str, dict] = {}

    candidates: list[tuple[str, Path, bool]] = [
        ("ref_fasta", refs.ref_fasta, True),
        ("fasta_index", refs.fasta_index, True),
        ("sequence_dict", refs.sequence_dict, settings.reference_require_dict),
    ]
    for sfx, path in refs.bwa_index_files().items():
        candidates.append((f"bwa{sfx}", path, sfx in {".amb", ".ann"}))

    if refs.known_sites_vcf:
        candidates.append(("known_sites", refs.known_sites_vcf, settings.reference_require_known_sites))
    if refs.clinvar_vcf:
        candidates.append(("clinvar", refs.clinvar_vcf, False))

    for name, path, required in candidates:
        if not path.is_file():
            continue
        try:
            rel_path = str(path.relative_to(refs.reference_dir))
        except ValueError:
            rel_path = str(path)
        files[name] = {
            "path": rel_path,
            "sha256": file_sha256(path),
            "size": path.stat().st_size,
            "required": required,
        }

    manifest = {
        "genome_build": refs.genome_build,
        "genome_version": version,
        "snpeff_db": refs.snpeff_db,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    refs.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def validate_reference_bundle(genome_build: str | None = None) -> ReferenceValidationResult:
    """چک‌لیست Pass/Fail: وجود فایل، checksum، نسخه ژنوم."""
    settings = get_settings()
    refs = get_reference_bundle(genome_build)
    checks: list[ReferenceCheck] = []

    # پوشه REFERENCE_DIR
    dir_ok = refs.reference_dir.is_dir()
    checks.append(
        ReferenceCheck(
            "reference_dir",
            str(refs.reference_dir),
            dir_ok,
            True,
            "حاضر" if dir_ok else "REFERENCE_DIR وجود ندارد",
        )
    )

    fasta_ok = refs.ref_fasta.is_file()
    checks.append(
        ReferenceCheck(
            "ref_fasta",
            str(refs.ref_fasta),
            fasta_ok,
            True,
            "حاضر" if fasta_ok else "فاستا یافت نشد",
        )
    )

    fai_ok = refs.fasta_index.is_file()
    checks.append(
        ReferenceCheck(
            "fasta_index",
            str(refs.fasta_index),
            fai_ok,
            True,
            "حاضر" if fai_ok else ".fai یافت نشد (samtools faidx)",
        )
    )

    dict_required = settings.reference_require_dict
    dict_ok = refs.sequence_dict.is_file()
    checks.append(
        ReferenceCheck(
            "sequence_dict",
            str(refs.sequence_dict),
            dict_ok,
            dict_required,
            "حاضر" if dict_ok else ".dict یافت نشد (gatk CreateSequenceDictionary)",
        )
    )

    # BWA indexes
    bwa_files = refs.bwa_index_files()
    for sfx in (".amb", ".ann"):
        path = bwa_files.get(sfx) or Path(str(refs.bwa_index_prefix) + sfx)
        ok = path.is_file()
        checks.append(
            ReferenceCheck(
                f"bwa{sfx}",
                str(path),
                ok,
                True,
                "حاضر" if ok else f"ایندکس BWA {sfx} یافت نشد",
            )
        )

    bwt_path = bwa_files.get(".bwt.2bit.64") or bwa_files.get(".bwt")
    bwt_ok = bwt_path is not None and bwt_path.is_file()
    checks.append(
        ReferenceCheck(
            "bwa_bwt",
            str(bwt_path or Path(str(refs.bwa_index_prefix) + ".bwt*")),
            bwt_ok,
            True,
            "حاضر" if bwt_ok else "ایندکس BWA .bwt / .bwt.2bit.64 یافت نشد",
        )
    )

    # known-sites (GATK)
    ks = refs.known_sites_vcf
    ks_ok = ks is not None and ks.is_file()
    checks.append(
        ReferenceCheck(
            "known_sites",
            str(ks or refs.known_sites_dir / "dbsnp.vcf.gz"),
            ks_ok,
            settings.reference_require_known_sites,
            "حاضر" if ks_ok else "known-sites/dbSNP یافت نشد (اختیاری مگر require=true)",
        )
    )

    # نسخه ژنوم از هدر فاستا / manifest
    header = _read_fasta_header(refs.ref_fasta) if fasta_ok else None
    guessed = _guess_build_from_header(header)
    version_ok = True
    version_detail = f"settings={refs.genome_version}"
    if guessed and guessed != refs.genome_build:
        version_ok = False
        version_detail = f"mismatch: header≈{guessed}, configured={refs.genome_build}"
    elif header:
        version_detail = f"header={header[:80]} | version={refs.genome_version}"
    checks.append(
        ReferenceCheck(
            "genome_version",
            str(refs.ref_fasta),
            version_ok if fasta_ok else False,
            True,
            version_detail if fasta_ok else "بدون فاستا قابل بررسی نیست",
        )
    )

    # checksum از manifest
    manifest_data = None
    if refs.manifest_path.is_file():
        try:
            manifest_data = json.loads(refs.manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            checks.append(
                ReferenceCheck(
                    "manifest",
                    str(refs.manifest_path),
                    False,
                    False,
                    "manifest نامعتبر",
                )
            )
        else:
            checks.append(
                ReferenceCheck(
                    "manifest",
                    str(refs.manifest_path),
                    True,
                    False,
                    f"version={manifest_data.get('genome_version')}",
                )
            )
            for key, meta in (manifest_data.get("files") or {}).items():
                rel = meta.get("path")
                if not rel:
                    continue
                path = refs.reference_dir / rel if not Path(rel).is_absolute() else Path(rel)
                if not path.is_file():
                    checks.append(
                        ReferenceCheck(
                            f"checksum:{key}",
                            str(path),
                            False,
                            bool(meta.get("required", False)),
                            "فایل manifest موجود نیست",
                        )
                    )
                    continue
                current = file_sha256(path)
                expected = meta.get("sha256")
                match = expected == current
                checks.append(
                    ReferenceCheck(
                        f"checksum:{key}",
                        str(path),
                        match,
                        bool(meta.get("required", False)),
                        f"sha256={current[:16]}…" if match else f"mismatch expected={str(expected)[:16]}",
                    )
                )
    else:
        checks.append(
            ReferenceCheck(
                "manifest",
                str(refs.manifest_path),
                False,
                False,
                "manifest هنوز ساخته نشده (write_reference_manifest)",
            )
        )

    if fasta_ok:
        size = refs.ref_fasta.stat().st_size
        size_mb = size / (1024 * 1024)
        checks.append(
            ReferenceCheck(
                "fasta_size",
                str(refs.ref_fasta),
                size > 0,
                True,
                f"{size_mb:.3f} MB — digest={file_sha256(refs.ref_fasta)[:12]}",
            )
        )

    failed_required = [c for c in checks if c.required and not c.ok]
    ready = len(failed_required) == 0
    return ReferenceValidationResult(
        genome_build=refs.genome_build,
        genome_version=refs.genome_version,
        ready=ready,
        overall="PASS" if ready else "FAIL",
        checks=checks,
        minio_bucket=settings.s3_reference_bucket,
        minio_prefix=f"{REFERENCE_PREFIX}/{refs.genome_build}",
        reference_dir=str(refs.reference_dir),
        manifest_path=str(refs.manifest_path) if refs.manifest_path.is_file() else None,
    )


def sync_reference_to_minio(
    genome_build: str | None = None,
    *,
    include_optional: bool = True,
    require_ready: bool = True,
) -> dict:
    """آپلود بسته مرجع به bucket جداگانه reference در MinIO."""
    from barekat_genomics.core.storage import get_reference_storage

    settings = get_settings()
    refs = get_reference_bundle(genome_build)
    if not refs.manifest_path.is_file():
        write_reference_manifest(genome_build)

    validation = validate_reference_bundle(genome_build)
    if require_ready and not validation.ready:
        raise FileNotFoundError(
            "مرجع ژنوم Pass نشده است. خروجی validation را ببینید و فایل‌های FAIL را تکمیل کنید."
        )

    storage = get_reference_storage()
    storage.ensure_bucket()
    prefix = f"{REFERENCE_PREFIX}/{refs.genome_build}"
    uploaded: list[str] = []

    files: list[Path] = []
    for path in (
        refs.ref_fasta,
        refs.fasta_index,
        refs.sequence_dict,
        refs.manifest_path,
    ):
        if path.is_file():
            files.append(path)
    files.extend(refs.bwa_index_files().values())
    if include_optional:
        if refs.known_sites_vcf and refs.known_sites_vcf.is_file():
            files.append(refs.known_sites_vcf)
        if refs.clinvar_vcf and refs.clinvar_vcf.is_file():
            files.append(refs.clinvar_vcf)
        if refs.pharmgkb_dir and refs.pharmgkb_dir.is_dir():
            files.extend(p for p in refs.pharmgkb_dir.rglob("*") if p.is_file())

    for path in dict.fromkeys(files):
        try:
            rel = path.relative_to(refs.reference_dir).as_posix()
        except ValueError:
            rel = path.name
        key = f"{prefix}/{rel}"
        storage.upload_file(path, key)
        uploaded.append(f"s3://{settings.s3_reference_bucket}/{key}")

    return {
        "bucket": settings.s3_reference_bucket,
        "prefix": prefix,
        "uploaded": uploaded,
        "validation": validation.to_dict(),
    }


def download_reference_from_minio(
    dest_dir: Path | str | None = None,
    genome_build: str | None = None,
) -> dict:
    """دانلود بسته مرجع از bucket مرجع MinIO به REFERENCE_DIR."""
    from barekat_genomics.core.storage import get_reference_storage

    settings = get_settings()
    build = genome_build or settings.genome_build
    target = Path(dest_dir) if dest_dir else Path(settings.reference_dir)
    target.mkdir(parents=True, exist_ok=True)

    storage = get_reference_storage()
    prefix = f"{REFERENCE_PREFIX}/{build}/"
    downloaded: list[str] = []

    try:
        keys = storage.list_keys(prefix)
    except Exception as exc:
        raise RuntimeError(f"لیست اشیای MinIO ناموفق ({settings.s3_reference_bucket}): {exc}") from exc

    if not keys:
        raise FileNotFoundError(
            f"هیچ شیئی زیر s3://{settings.s3_reference_bucket}/{prefix} یافت نشد"
        )

    for key in keys:
        rel = key[len(prefix) :] if key.startswith(prefix) else Path(key).name
        local_path = target / rel
        storage.download_file(key, local_path)
        downloaded.append(str(local_path))

    # رفرش مسیرهای تنظیمات نسبت به dest
    validation = validate_reference_bundle(build)
    return {
        "bucket": settings.s3_reference_bucket,
        "dest_dir": str(target),
        "downloaded": downloaded,
        "validation": validation.to_dict(),
    }


def _transfer(src: Path, dest: Path, *, copy: bool) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() == dest.resolve():
        return
    if copy:
        shutil.copy2(src, dest)
    else:
        if dest.exists():
            dest.unlink()
        try:
            src.replace(dest)
        except OSError:
            shutil.copy2(src, dest)
