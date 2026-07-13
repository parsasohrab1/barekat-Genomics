#!/usr/bin/env nextflow

/*
 * barekat Genomics — reproducible pharmacogenomic pipeline
 * QC → alignment (FASTQ) → variant calling → interpretation → report JSON
 */

nextflow.enable.dsl = 2

params.input       = ''
params.file_type   = 'BAM'
params.genome_build = 'GRCh38'
params.job_id      = 'local'
params.outdir      = './results'
params.reference_dir = '/data/reference/GRCh38'

workflow {
    if (!params.input) {
        exit 1, "ERROR: --input required"
    }

    Channel.of(
        tuple(params.job_id, file(params.input), params.file_type, params.genome_build)
    ).set { sample_ch }

    RUN_PIPELINE(sample_ch)
}

process RUN_PIPELINE {
    tag "${job_id}"
    publishDir "${params.outdir}/${job_id}", mode: 'copy'

    input:
    tuple val(job_id), path(input_file), val(file_type), val(genome_build)

    output:
    path "pipeline_result.json", emit: result

    script:
    """
    python -m barekat_genomics.pipeline.workflow_cli \\
        --job-id ${job_id} \\
        --input ${input_file} \\
        --file-type ${file_type} \\
        --genome-build ${genome_build} \\
        --output pipeline_result.json
    """
}
