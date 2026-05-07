from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolStatus(BaseModel):
    name: str
    available: bool
    version: str | None = None
    path: str | None = None
    required: bool = True
    message: str | None = None


class HealthResponse(BaseModel):
    app: str = "ReadQraft"
    version: str
    status: str = "ok"


class SampleStatus(str, Enum):
    paired = "paired-end"
    single = "single-end"
    incomplete = "missing-pair"


class DetectedSample(BaseModel):
    sample_id: str
    r1_file: str | None = None
    r2_file: str | None = None
    status: SampleStatus
    warnings: list[str] = Field(default_factory=list)


class UploadedFileInfo(BaseModel):
    filename: str
    size_bytes: int
    sha256: str


class UploadResponse(BaseModel):
    project_id: str
    files: list[UploadedFileInfo]
    samples: list[DetectedSample]
    warnings: list[str] = Field(default_factory=list)


class RunOptions(BaseModel):
    mode: str = "simple"
    trimming_engine: str = "fastp"
    phred_quality_threshold: int = Field(default=20, ge=0, le=40)
    minimum_read_length: int = Field(default=50, ge=1, le=10000)
    adapter_sequence: str | None = None
    auto_detect_adapters: bool = True
    poly_g_trimming: bool = True
    poly_x_trimming: bool = False
    threads: int = Field(default=4, ge=1, le=128)
    keep_intermediate_files: bool = True
    generate_methods_text: bool = True
    generate_checksums: bool = True
    show_command_preview: bool = False


class RunResponse(BaseModel):
    job_id: str
    project_id: str
    status: str


class JobEvent(BaseModel):
    job_id: str
    status: str
    step: str
    message: str
    progress: int = Field(ge=0, le=100)
    sample_id: str | None = None
    level: str = "info"


class JobStatus(BaseModel):
    job_id: str
    project_id: str
    status: str
    progress: int
    current_step: str
    events: list[JobEvent] = Field(default_factory=list)


class ProjectResults(BaseModel):
    project_id: str
    status: str
    samples: list[dict[str, Any]]
    reports: list[dict[str, str]]
    downloads: dict[str, str]
    methods_text: str | None = None
