#!/usr/bin/env python3
"""Management of the GRCh38/hg38 genome reference — local and MinIO.

Usage:
  python scripts/setup_reference.py ensure-layout
  python scripts/setup_reference.py install-local --source /path/to/grch38
  python scripts/setup_reference.py write-manifest
  python scripts/setup_reference.py validate
  python scripts/setup_reference.py upload-minio
  python scripts/setup_reference.py download-minio
  python scripts/setup_reference.py create-demo   # for testing only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from barekat_genomics.pipeline.reference import (  # noqa: E402
    download_reference_from_minio,
    ensure_reference_layout,
    install_reference_from_local,
    sync_reference_to_minio,
    validate_reference_bundle,
    write_reference_manifest,
)


def _print(payload: dict) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        print(text)
    except UnicodeEncodeError:
        print(json.dumps(payload, ensure_ascii=True, indent=2))


def _create_demo(dest: Path, build: str = "GRCh38") -> dict:
    """Mini-reference structure for validation / MinIO tests (not for real production)."""
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "known-sites").mkdir(exist_ok=True)

    fasta = dest / f"{build}.fa"
    fasta.write_text(
        f">chr1 {build}\n"
        "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT\n"
        "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT\n",
        encoding="utf-8",
    )
    # minimal fai
    (dest / f"{build}.fa.fai").write_text("chr1\t128\t6\t64\t65\n", encoding="utf-8")
    # minimal dict similar to Picard
    (dest / f"{build}.dict").write_text(
        f"@HD\tVN:1.6\tSO:unsorted\n@SQ\tSN:chr1\tLN:128\tAS:{build}\n",
        encoding="utf-8",
    )
    # fake BWA-MEM2 index files
    for sfx in (".amb", ".ann", ".bwt.2bit.64", ".pac", ".0123"):
        (dest / f"{build}{sfx}").write_bytes(b"DEMO_INDEX_" + sfx.encode())

    (dest / "known-sites" / "dbsnp.vcf.gz").write_bytes(b"##demo\n")

    return {
        "demo_dir": str(dest),
        "note": "The demo files are only for validation/MinIO testing",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="GRCh38 reference setup & validation")
    parser.add_argument(
        "action",
        choices=[
            "ensure-layout",
            "install-local",
            "write-manifest",
            "validate",
            "upload-minio",
            "download-minio",
            "create-demo",
        ],
    )
    parser.add_argument("--genome-build", default=None)
    parser.add_argument("--genome-version", default=None)
    parser.add_argument("--source", default=None, help="Local source dir for install-local")
    parser.add_argument("--dest", default=None, help="Download/demo destination")
    parser.add_argument("--move", action="store_true", help="Move instead of copy on install-local")
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Upload even if validation is FAIL",
    )
    args = parser.parse_args()

    if args.action == "ensure-layout":
        path = ensure_reference_layout(args.genome_build)
        _print({"reference_dir": str(path)})
        return 0

    if args.action == "create-demo":
        import os

        dest = Path(args.dest) if args.dest else Path(os.environ.get("REFERENCE_DIR", "data/reference/GRCh38"))
        info = _create_demo(dest, build=args.genome_build or "GRCh38")
        # we do not temporarily set the env for the manifest on this path;
        # the user must point REFERENCE_DIR to dest.
        _print(info)
        return 0

    if args.action == "install-local":
        if not args.source:
            print("ERROR: --source is required for install-local", file=sys.stderr)
            return 2
        info = install_reference_from_local(
            args.source,
            genome_build=args.genome_build,
            genome_version=args.genome_version,
            copy=not args.move,
        )
        _print(info)
        return 0 if info["validation"]["ready"] else 1

    if args.action == "write-manifest":
        manifest = write_reference_manifest(args.genome_build, genome_version=args.genome_version)
        _print(manifest)
        return 0

    if args.action == "validate":
        result = validate_reference_bundle(args.genome_build)
        _print(result.to_dict())
        return 0 if result.ready else 1

    if args.action == "upload-minio":
        info = sync_reference_to_minio(
            args.genome_build,
            require_ready=not args.allow_incomplete,
        )
        _print(info)
        return 0

    if args.action == "download-minio":
        info = download_reference_from_minio(args.dest, args.genome_build)
        _print(info)
        return 0 if info["validation"]["ready"] else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
