"""CLI entrypoint for Nextflow/Snakemake/K8s/AWS Batch workers."""

from __future__ import annotations

import argparse
import json
import sys
import uuid

from barekat_genomics.core.database import SessionLocal
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.services.pipeline_service import PipelineService


def main() -> int:
    parser = argparse.ArgumentParser(description="Run barekat pipeline job")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--file-type", default="BAM")
    parser.add_argument("--genome-build", default="GRCh38")
    parser.add_argument("--sample-id", default=None, help="DB sample UUID (optional)")
    parser.add_argument("--output", default="-", help="Write result JSON path or - for stdout")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        service = PipelineService(db)
        job = service.get_job(uuid.UUID(args.job_id))
        if job:
            sample = db.query(SequencingSample).filter(SequencingSample.id == job.sample_id).first()
            if sample:
                service._execute_pipeline(job, sample)
                result = {
                    "status": job.status,
                    "job_id": str(job.id),
                    "stage": job.stage,
                    "error": job.error_message,
                }
            else:
                result = {"status": "error", "message": "sample not found"}
        else:
            from barekat_genomics.pipeline.orchestrator import run_full_pipeline

            pipeline_result = run_full_pipeline(
                args.input,
                args.file_type,
                args.genome_build,
                sample_label=args.job_id,
            )
            result = {
                "status": "completed" if pipeline_result.success else "failed",
                "job_id": args.job_id,
                "variant_count": len(pipeline_result.variants),
                "error": pipeline_result.error,
            }

        payload = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output == "-":
            print(payload)
        else:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(payload)
        return 0 if result.get("status") in ("completed", "pending") else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
