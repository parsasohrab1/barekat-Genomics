#!/usr/bin/env python3
"""ایجاد بیماران، نمونه‌ها و گزارش‌های سنتتیک برای توسعه."""

import sys

from barekat_genomics.core.database import SessionLocal
from barekat_genomics.models.patient import Patient
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.services.pipeline_service import PipelineService

from data.dev_fixtures import DEV_PATIENTS, DEV_SAMPLES


def seed_dev_data(*, run_pipeline: bool = True) -> None:
    db = SessionLocal()
    try:
        patient_map: dict[str, Patient] = {}
        for pdata in DEV_PATIENTS:
            existing = db.query(Patient).filter(Patient.external_id == pdata["external_id"]).first()
            if existing:
                patient_map[pdata["external_id"]] = existing
                print(f"  skip patient {pdata['external_id']}")
                continue
            p = Patient(
                external_id=pdata["external_id"],
                age=pdata["age"],
                gender=pdata["gender"],
                clinical_notes=pdata["clinical_notes"],
            )
            db.add(p)
            db.flush()
            patient_map[pdata["external_id"]] = p
            print(f"  + patient {pdata['external_id']}")

        db.commit()

        sample_map: dict[str, SequencingSample] = {}
        for sdata in DEV_SAMPLES:
            existing = db.query(SequencingSample).filter(SequencingSample.sample_id == sdata["sample_id"]).first()
            if existing:
                sample_map[sdata["sample_id"]] = existing
                print(f"  skip sample {sdata['sample_id']}")
                continue
            patient = patient_map.get(sdata["patient_external_id"])
            if not patient:
                print(f"  ! patient missing for {sdata['sample_id']}")
                continue
            sample = SequencingSample(
                patient_id=patient.id,
                sample_id=sdata["sample_id"],
                file_type=sdata["file_type"],
                storage_path=f"/dev/synthetic/{sdata['sample_id']}.bam",
                status="uploaded",
                genome_build="GRCh38",
            )
            db.add(sample)
            db.flush()
            sample_map[sdata["sample_id"]] = sample
            print(f"  + sample {sdata['sample_id']}")

        db.commit()

        if not run_pipeline:
            return

        pipeline = PipelineService(db)
        for sdata in DEV_SAMPLES:
            sample = sample_map.get(sdata["sample_id"])
            if not sample or sample.status == "processed":
                continue
            module = sdata.get("module", "pharmacogenomics")
            print(f"  > pipeline {sample.sample_id} ({module})")
            pipeline.start_pipeline(
                sample.id,
                async_mode=False,
                module=module,
            )
            print(f"    done — status {sample.status}")

    finally:
        db.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("==> Seeding dev data...")
    seed_dev_data(run_pipeline="--no-pipeline" not in sys.argv)
    print("==> Done.")
