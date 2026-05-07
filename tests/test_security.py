from pathlib import Path

import pytest

from app.security import ensure_within_directory, is_fastq_filename, sanitize_filename, validate_project_id


def test_validate_project_id_blocks_path_traversal():
    with pytest.raises(ValueError):
        validate_project_id("../outside")


def test_sanitize_filename_keeps_basename():
    assert sanitize_filename("../../Sample A_R1.fastq.gz") == "Sample_A_R1.fastq.gz"


def test_fastq_extensions():
    assert is_fastq_filename("reads.fastq.gz")
    assert is_fastq_filename("reads.fq")
    assert not is_fastq_filename("reads.txt")


def test_ensure_within_directory(tmp_path: Path):
    base = tmp_path / "base"
    base.mkdir()
    inside = base / "file.txt"
    inside.write_text("ok")
    assert ensure_within_directory(base, inside) == inside.resolve()
    with pytest.raises(ValueError):
        ensure_within_directory(base, tmp_path / "outside.txt")
