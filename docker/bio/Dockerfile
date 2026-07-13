# Bioinformatics worker image
# Tools: FastQC, MultiQC, BWA-MEM2, samtools, GATK4, SnpEff, bcftools
FROM mambaorg/micromamba:1.5.10-jammy

USER root
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    procps curl \
    && rm -rf /var/lib/apt/lists/*

COPY docker/bio/environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml \
    && micromamba clean -a --yes

ENV PATH="/opt/conda/bin:${PATH}"
ENV PIPELINE_MODE=production
ENV PIPELINE_WORK_DIR=/data/processed
ENV REFERENCE_DIR=/data/reference/GRCh38
ENV MAMBA_DOCKERFILE_ACTIVATE=1

# Python application (Celery worker)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

ENV PYTHONPATH=/app/src

VOLUME ["/data"]

CMD ["celery", "-A", "barekat_genomics.tasks.celery_app", "worker", "--loglevel=info", "--concurrency=1"]
