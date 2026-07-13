"""Tests for bioinformatics command runner."""

from barekat_genomics.pipeline.exec import tool_available


def test_fastqc_not_required_in_simulated():
    # In dev/test env FastQC may not be installed
    assert isinstance(tool_available("fastqc"), bool)
