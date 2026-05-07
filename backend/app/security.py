from __future__ import annotations

import re
from pathlib import Path

SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")
FASTQ_EXTENSIONS = (
    ".fastq",
    ".fq",
    ".fastq.gz",
    ".fq.gz",
)


def validate_project_id(project_id: str) -> str:
    if not SAFE_ID_RE.match(project_id):
        raise ValueError("Project ID contains unsupported characters.")
    return project_id


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name.strip().replace(" ", "_")
    name = SAFE_NAME_RE.sub("_", name)
    if not name or name in {".", ".."}:
        raise ValueError("Filename is empty after sanitization.")
    return name


def is_fastq_filename(filename: str) -> bool:
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in FASTQ_EXTENSIONS)


def ensure_within_directory(base: Path, candidate: Path) -> Path:
    base_resolved = base.resolve()
    candidate_resolved = candidate.resolve()
    if base_resolved != candidate_resolved and base_resolved not in candidate_resolved.parents:
        raise ValueError("Path traversal blocked.")
    return candidate_resolved
