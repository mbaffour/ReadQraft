from __future__ import annotations

import re
from pathlib import Path

from app.models.schemas import DetectedSample, SampleStatus

PAIR_PATTERNS = [
    (re.compile(r"(.+?)(?:_|\.|-)R?1(?:_|\.|-|$)(.*)", re.IGNORECASE), "r1"),
    (re.compile(r"(.+?)(?:_|\.|-)R?2(?:_|\.|-|$)(.*)", re.IGNORECASE), "r2"),
    (re.compile(r"(.+?)(?:forward)(.*)", re.IGNORECASE), "r1"),
    (re.compile(r"(.+?)(?:reverse)(.*)", re.IGNORECASE), "r2"),
]


def _strip_fastq_suffix(name: str) -> str:
    lower = name.lower()
    for suffix in [".fastq.gz", ".fq.gz", ".fastq", ".fq"]:
        if lower.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _sample_key(filename: str) -> tuple[str, str | None]:
    stem = _strip_fastq_suffix(Path(filename).name)
    for pattern, mate in PAIR_PATTERNS:
        match = pattern.match(stem)
        if match:
            sample = (match.group(1) + match.group(2)).strip("_.-")
            return sample or stem, mate
    return stem, None


def detect_samples(filenames: list[str]) -> list[DetectedSample]:
    grouped: dict[str, dict[str, str | None]] = {}
    warnings: dict[str, list[str]] = {}
    for filename in sorted(filenames):
        sample_id, mate = _sample_key(filename)
        grouped.setdefault(sample_id, {"r1": None, "r2": None, "single": None})
        warnings.setdefault(sample_id, [])
        if mate == "r1":
            if grouped[sample_id]["r1"]:
                warnings[sample_id].append("Duplicate R1 candidate detected.")
            grouped[sample_id]["r1"] = filename
        elif mate == "r2":
            if grouped[sample_id]["r2"]:
                warnings[sample_id].append("Duplicate R2 candidate detected.")
            grouped[sample_id]["r2"] = filename
        else:
            grouped[sample_id]["single"] = filename

    samples: list[DetectedSample] = []
    for sample_id, mates in grouped.items():
        if mates["r1"] and mates["r2"]:
            status = SampleStatus.paired
        elif mates["r1"] or mates["r2"]:
            status = SampleStatus.incomplete
            warnings[sample_id].append("R2 file missing [paired-end reads require both forward and reverse files]." if mates["r1"] else "R1 file missing [paired-end reads require both forward and reverse files].")
        else:
            status = SampleStatus.single
        samples.append(
            DetectedSample(
                sample_id=sample_id,
                r1_file=mates["r1"] or mates["single"],
                r2_file=mates["r2"],
                status=status,
                warnings=warnings[sample_id],
            )
        )
    return samples
