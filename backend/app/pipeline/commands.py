from __future__ import annotations

from pathlib import Path

from app.models.schemas import DetectedSample, RunOptions, SampleStatus


def fastqc_command(input_file: Path, output_dir: Path, threads: int) -> list[str]:
    return ["fastqc", str(input_file), "-o", str(output_dir), "--threads", str(threads)]


def fastp_command(sample: DetectedSample, root: Path, options: RunOptions) -> list[str]:
    raw = root / "raw"
    trimmed = root / "trimmed"
    reports = root / "reports"
    base = sample.sample_id
    r1_output = trimmed / (f"{base}_R1.trimmed.fastq.gz" if sample.status == SampleStatus.paired else f"{base}.trimmed.fastq.gz")
    cmd = [
        "fastp",
        "-i",
        str(raw / sample.r1_file),
        "-o",
        str(r1_output),
        "--qualified_quality_phred",
        str(options.phred_quality_threshold),
        "--length_required",
        str(options.minimum_read_length),
        "--html",
        str(reports / f"{base}.fastp.html"),
        "--json",
        str(reports / f"{base}.fastp.json"),
        "--thread",
        str(options.threads),
    ]
    if sample.status == SampleStatus.paired and sample.r2_file:
        cmd.extend(["-I", str(raw / sample.r2_file), "-O", str(trimmed / f"{base}_R2.trimmed.fastq.gz")])
        if options.auto_detect_adapters:
            cmd.append("--detect_adapter_for_pe")
    if options.adapter_sequence:
        cmd.extend(["--adapter_sequence", options.adapter_sequence])
    if options.poly_g_trimming:
        cmd.append("--trim_poly_g")
    if options.poly_x_trimming:
        cmd.append("--trim_poly_x")
    return cmd


def cutadapt_command(sample: DetectedSample, root: Path, options: RunOptions) -> list[str]:
    raw = root / "raw"
    trimmed = root / "trimmed"
    reports = root / "reports"
    base = sample.sample_id
    r1_output = trimmed / (f"{base}_R1.trimmed.fastq.gz" if sample.status == SampleStatus.paired else f"{base}.trimmed.fastq.gz")
    cmd = [
        "python",
        "-m",
        "cutadapt",
        "-q",
        str(options.phred_quality_threshold),
        "-m",
        str(options.minimum_read_length),
        "-j",
        str(options.threads),
        "--report",
        "full",
        "-o",
        str(r1_output),
    ]
    if options.adapter_sequence:
        cmd.extend(["-a", options.adapter_sequence])
    if sample.status == SampleStatus.paired and sample.r2_file:
        cmd.extend(["-p", str(trimmed / f"{base}_R2.trimmed.fastq.gz")])
        if options.adapter_sequence:
            cmd.extend(["-A", options.adapter_sequence])
        cmd.extend([str(raw / sample.r1_file), str(raw / sample.r2_file)])
    else:
        cmd.append(str(raw / sample.r1_file))
    return cmd


def multiqc_command(root: Path) -> list[str]:
    return ["python", "-m", "multiqc", str(root), "-o", str(root / "multiqc"), "--force"]
