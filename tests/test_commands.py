from pathlib import Path

from app.models.schemas import DetectedSample, RunOptions, SampleStatus
from app.pipeline.commands import cutadapt_command, fastp_command, fastqc_command, multiqc_command


def test_fastqc_command_uses_argument_array():
    cmd = fastqc_command(Path("input.fastq.gz"), Path("qc"), 4)
    assert cmd == ["fastqc", "input.fastq.gz", "-o", "qc", "--threads", "4"]


def test_fastp_paired_command():
    sample = DetectedSample(sample_id="S1", r1_file="S1_R1.fastq.gz", r2_file="S1_R2.fastq.gz", status=SampleStatus.paired)
    cmd = fastp_command(sample, Path("/project"), RunOptions())
    assert "--detect_adapter_for_pe" in cmd
    assert "-I" in cmd
    assert "/project/trimmed/S1_R2.trimmed.fastq.gz" in cmd


def test_multiqc_command():
    assert multiqc_command(Path("/project")) == ["python", "-m", "multiqc", "/project", "-o", "/project/multiqc", "--force"]


def test_cutadapt_paired_command():
    sample = DetectedSample(sample_id="S1", r1_file="S1_R1.fastq.gz", r2_file="S1_R2.fastq.gz", status=SampleStatus.paired)
    cmd = cutadapt_command(sample, Path("/project"), RunOptions(adapter_sequence="AGATCGGA"))
    assert cmd[:3] == ["python", "-m", "cutadapt"]
    assert "-p" in cmd
    assert "-a" in cmd
    assert "-A" in cmd
    assert "/project/trimmed/S1_R2.trimmed.fastq.gz" in cmd
