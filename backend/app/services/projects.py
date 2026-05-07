from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import data_root
from app.models.schemas import UploadedFileInfo
from app.security import (
    ensure_within_directory,
    is_fastq_filename,
    sanitize_filename,
    validate_project_id,
)
from app.utils.checksums import sha256_file

PROJECT_DIRS = [
    "raw",
    "qc_raw",
    "trimmed",
    "qc_trimmed",
    "multiqc",
    "logs",
    "reports",
    "reproducibility",
]


def new_project_id() -> str:
    return f"rq_{uuid.uuid4().hex[:12]}"


def project_root(project_id: str) -> Path:
    validate_project_id(project_id)
    root = data_root() / project_id
    return ensure_within_directory(data_root(), root)


def create_project(project_id: str | None = None) -> Path:
    pid = validate_project_id(project_id or new_project_id())
    root = project_root(pid)
    root.mkdir(parents=True, exist_ok=True)
    for folder in PROJECT_DIRS:
        (root / folder).mkdir(exist_ok=True)
    return root


async def save_uploads(project_id: str, files: list[UploadFile]) -> tuple[list[UploadedFileInfo], list[str]]:
    root = create_project(project_id)
    raw_dir = root / "raw"
    uploaded: list[UploadedFileInfo] = []
    warnings: list[str] = []
    seen: set[str] = set()

    for upload in files:
        safe_name = sanitize_filename(upload.filename or "upload.fastq.gz")
        if safe_name in seen or (raw_dir / safe_name).exists():
            raise ValueError(f"Duplicate filename: {safe_name}")
        seen.add(safe_name)
        if not is_fastq_filename(safe_name):
            raise ValueError(f"Unsupported file extension: {safe_name}")
        destination = ensure_within_directory(raw_dir, raw_dir / safe_name)
        size = 0
        with destination.open("wb") as out:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                out.write(chunk)
        if size == 0:
            warnings.append(f"{safe_name} is empty.")
        uploaded.append(UploadedFileInfo(filename=safe_name, size_bytes=size, sha256=sha256_file(destination)))
    write_project_state(project_id, {"project_id": project_id, "files": [item.model_dump() for item in uploaded]})
    return uploaded, warnings


def write_project_state(project_id: str, state: dict) -> None:
    root = create_project(project_id)
    state_path = ensure_within_directory(root, root / "project.json")
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def read_project_state(project_id: str) -> dict:
    path = project_root(project_id) / "project.json"
    if not path.exists():
        return {"project_id": project_id}
    return json.loads(path.read_text(encoding="utf-8"))


def cleanup_project(project_id: str) -> None:
    root = project_root(project_id)
    if root.exists():
        shutil.rmtree(root)
