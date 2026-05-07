from __future__ import annotations

import asyncio
import gzip
import json
import platform
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app import __version__
from app.config import APP_VERSION, apply_tool_environment, mock_tools_enabled
from app.models.schemas import DetectedSample, JobEvent, JobStatus, RunOptions, SampleStatus
from app.pipeline.commands import cutadapt_command, fastp_command, fastqc_command, multiqc_command
from app.security import ensure_within_directory
from app.services.projects import create_project, project_root, read_project_state, write_project_state
from app.services.samples import detect_samples
from app.services.tools import tools_by_name
from app.utils.checksums import sha256_file


class JobManager:
    def __init__(self) -> None:
        self.jobs: dict[str, JobStatus] = {}
        self.queues: dict[str, asyncio.Queue[JobEvent]] = {}
        self.tasks: dict[str, asyncio.Task] = {}
        self.cancelled: set[str] = set()

    def create_job(self, job_id: str, project_id: str, options: RunOptions) -> JobStatus:
        status = JobStatus(job_id=job_id, project_id=project_id, status="queued", progress=0, current_step="Queued")
        self.jobs[job_id] = status
        self.queues[job_id] = asyncio.Queue()
        self.tasks[job_id] = asyncio.create_task(run_pipeline(self, job_id, project_id, options))
        return status

    async def emit(self, event: JobEvent) -> None:
        status = self.jobs[event.job_id]
        status.status = event.status
        status.progress = event.progress
        status.current_step = event.step
        status.events.append(event)
        await self.queues[event.job_id].put(event)

    def cancel(self, job_id: str) -> None:
        self.cancelled.add(job_id)
        task = self.tasks.get(job_id)
        if task:
            task.cancel()


job_manager = JobManager()


async def run_pipeline(manager: JobManager, job_id: str, project_id: str, options: RunOptions) -> None:
    root = create_project(project_id)
    command_log: list[dict[str, Any]] = []
    try:
        await _emit(manager, job_id, "running", "Checking FASTQ integrity", "Checking FASTQ integrity [making sure files look valid]", 5)
        raw_files = sorted(p.name for p in (root / "raw").iterdir() if p.is_file())
        samples = detect_samples(raw_files)
        if not raw_files:
            raise RuntimeError("No FASTQ files were uploaded.")
        if any(sample.status == SampleStatus.incomplete for sample in samples):
            raise RuntimeError("One or more paired-end samples are missing R1 or R2 files.")

        tools = tools_by_name()
        trimming_engine = _select_trimming_engine(options.trimming_engine, tools)
        use_mock = mock_tools_enabled() and not (tools["fastqc"].available and tools["multiqc"].available and bool(trimming_engine))
        await _emit(manager, job_id, "running", "Detecting read pairing", f"Detected {len(samples)} sample(s).", 12)

        await _emit(manager, job_id, "running", "Running raw FastQC", "Running raw FastQC [quality check before trimming]", 22)
        for sample in samples:
            for filename in [sample.r1_file, sample.r2_file]:
                if filename:
                    await _run_or_mock(fastqc_command(root / "raw" / filename, root / "qc_raw", options.threads), root, command_log, use_mock, sample.sample_id)

        if not trimming_engine and not use_mock:
            raise RuntimeError("No supported trimming engine found [ReadQraft requires fastp or Cutadapt].")
        engine_label = trimming_engine or options.trimming_engine
        await _emit(manager, job_id, "running", f"Running {engine_label}", f"Running {engine_label} [adapter and quality trimming]", 42)
        for sample in samples:
            if engine_label == "cutadapt":
                await _run_or_mock(cutadapt_command(sample, root, options), root, command_log, use_mock, sample.sample_id)
                if not use_mock:
                    _write_cutadapt_summary(root, sample, options)
            else:
                await _run_or_mock(fastp_command(sample, root, options), root, command_log, use_mock, sample.sample_id)
            if use_mock:
                _write_mock_trimmed_files(root, sample)

        await _emit(manager, job_id, "running", "Running post-trim FastQC", "Running post-trim FastQC [quality check after trimming]", 62)
        for fastq in sorted((root / "trimmed").glob("*.fastq.gz")):
            await _run_or_mock(fastqc_command(fastq, root / "qc_trimmed", options.threads), root, command_log, use_mock, fastq.stem)

        await _emit(manager, job_id, "running", "Running MultiQC", "Running MultiQC [combining reports]", 76)
        await _run_or_mock(multiqc_command(root), root, command_log, use_mock, None)
        if use_mock:
            (root / "multiqc" / "multiqc_report.html").write_text("<html><body><h1>ReadQraft development mock MultiQC report</h1></body></html>", encoding="utf-8")

        await _emit(manager, job_id, "running", "Generating reproducibility package", "Saving logs, commands, versions, checksums, and methods text.", 88)
        results = _build_results(root, samples, options, command_log, tools, use_mock, engine_label)
        _write_reproducibility(root, project_id, samples, options, command_log, tools, results, use_mock)
        zip_path = _zip_reproducibility(root)
        state = read_project_state(project_id)
        state.update({"status": "complete", "samples": [s.model_dump() for s in samples], "results": results, "reproducibility_zip": zip_path.name})
        write_project_state(project_id, state)
        await _emit(manager, job_id, "complete", "Complete", "Analysis complete.", 100)
    except asyncio.CancelledError:
        await _emit(manager, job_id, "cancelled", "Cancelled", "Analysis was cancelled.", 100, level="warning")
    except Exception as exc:
        state = read_project_state(project_id)
        state.update({"status": "failed", "error": str(exc)})
        write_project_state(project_id, state)
        await _emit(manager, job_id, "failed", "Failed", str(exc), 100, level="error")


async def _emit(manager: JobManager, job_id: str, status: str, step: str, message: str, progress: int, sample_id: str | None = None, level: str = "info") -> None:
    await manager.emit(JobEvent(job_id=job_id, status=status, step=step, message=message, progress=progress, sample_id=sample_id, level=level))


def _select_trimming_engine(requested: str, tools: dict[str, Any]) -> str | None:
    normalized = requested.lower()
    if normalized == "fastp" and tools["fastp"].available:
        return "fastp"
    if normalized == "cutadapt" and tools["cutadapt"].available:
        return "cutadapt"
    if tools["fastp"].available:
        return "fastp"
    if tools["cutadapt"].available:
        return "cutadapt"
    return None


async def _run_or_mock(cmd: list[str], root: Path, command_log: list[dict[str, Any]], use_mock: bool, sample_id: str | None) -> None:
    apply_tool_environment()
    started = datetime.now(timezone.utc).isoformat()
    entry: dict[str, Any] = {"command": cmd, "sample_id": sample_id, "started_at": started, "mock": use_mock}
    if use_mock:
        entry.update({"return_code": 0, "stdout": "Development mock mode: command was not executed.", "stderr": "", "finished_at": datetime.now(timezone.utc).isoformat()})
        command_log.append(entry)
        return
    proc = await asyncio.to_thread(subprocess.run, cmd, cwd=str(root), capture_output=True, text=True, check=False)
    entry.update({"return_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr, "finished_at": datetime.now(timezone.utc).isoformat()})
    command_log.append(entry)
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed for {sample_id or 'project'} [returned exit code {proc.returncode}].")


def _write_mock_trimmed_files(root: Path, sample: DetectedSample) -> None:
    if sample.status == SampleStatus.paired:
        (root / "trimmed" / f"{sample.sample_id}_R1.trimmed.fastq.gz").write_bytes(b"")
        (root / "trimmed" / f"{sample.sample_id}_R2.trimmed.fastq.gz").write_bytes(b"")
    else:
        (root / "trimmed" / f"{sample.sample_id}.trimmed.fastq.gz").write_bytes(b"")
    (root / "reports" / f"{sample.sample_id}.fastp.html").write_text("<html><body><h1>ReadQraft development mock fastp report</h1></body></html>", encoding="utf-8")
    (root / "reports" / f"{sample.sample_id}.fastp.json").write_text(json.dumps({"summary": {"before_filtering": {"total_reads": 0}, "after_filtering": {"total_reads": 0}}}, indent=2), encoding="utf-8")


def _write_cutadapt_summary(root: Path, sample: DetectedSample, options: RunOptions) -> None:
    before = sum(_count_fastq_reads(root / "raw" / filename) for filename in [sample.r1_file, sample.r2_file] if filename)
    after = sum(_count_fastq_reads(path) for path in _trimmed_paths(root, sample) if path.exists())
    summary = {
        "summary": {
            "before_filtering": {"total_reads": before},
            "after_filtering": {"total_reads": after},
        },
        "engine": "cutadapt",
        "qualified_quality_phred": options.phred_quality_threshold,
        "length_required": options.minimum_read_length,
    }
    (root / "reports" / f"{sample.sample_id}.cutadapt.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def _trimmed_paths(root: Path, sample: DetectedSample) -> list[Path]:
    if sample.status == SampleStatus.paired:
        return [root / "trimmed" / f"{sample.sample_id}_R1.trimmed.fastq.gz", root / "trimmed" / f"{sample.sample_id}_R2.trimmed.fastq.gz"]
    return [root / "trimmed" / f"{sample.sample_id}.trimmed.fastq.gz"]


def _count_fastq_reads(path: Path) -> int:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle) // 4


def _build_results(root: Path, samples: list[DetectedSample], options: RunOptions, command_log: list[dict[str, Any]], tools: dict[str, Any], use_mock: bool, engine_used: str) -> dict[str, Any]:
    sample_rows = []
    for sample in samples:
        fastp_json = root / "reports" / f"{sample.sample_id}.fastp.json"
        cutadapt_json = root / "reports" / f"{sample.sample_id}.cutadapt.json"
        before = after = retention = None
        summary_path = fastp_json if fastp_json.exists() else cutadapt_json
        if summary_path.exists():
            parsed = json.loads(summary_path.read_text(encoding="utf-8"))
            before = parsed.get("summary", {}).get("before_filtering", {}).get("total_reads")
            after = parsed.get("summary", {}).get("after_filtering", {}).get("total_reads")
            retention = round((after / before) * 100, 2) if before else None
        sample_rows.append({"sample_id": sample.sample_id, "status": sample.status, "reads_before": before, "reads_after": after, "retention_percent": retention})
    methods = _methods_text(options, tools, engine_used)
    return {"samples": sample_rows, "methods_text": methods, "mock_mode": use_mock, "commands": command_log, "trimming_engine_used": engine_used}


def _methods_text(options: RunOptions, tools: dict[str, Any], engine_used: str) -> str:
    def version(name: str) -> str:
        value = tools.get(name)
        return value.version if value and value.version else "version not recorded"

    engine_version = version(engine_used)
    adapter_policy = "automatic adapter detection" if engine_used == "fastp" and options.auto_detect_adapters else "user-specified adapter settings" if options.adapter_sequence else "quality and length filtering"
    return (
        f"Raw FASTQ reads were assessed using FastQC ({version('fastqc')}). "
        f"Adapter and quality trimming were performed using {engine_used} ({engine_version}) "
        f"with {adapter_policy}, "
        f"a Phred quality threshold of Q{options.phred_quality_threshold}, and a minimum read length of {options.minimum_read_length} bp. "
        f"Trimmed reads were reassessed using FastQC, and QC summaries were aggregated using MultiQC ({version('multiqc')}). "
        "Tool versions, command-line parameters, logs, and file checksums were recorded for reproducibility."
    )


def _write_reproducibility(root: Path, project_id: str, samples: list[DetectedSample], options: RunOptions, command_log: list[dict[str, Any]], tools: dict[str, Any], results: dict[str, Any], use_mock: bool) -> None:
    repro = root / "reproducibility"
    repro.mkdir(exist_ok=True)
    (repro / "commands.txt").write_text("\n".join(" ".join(entry["command"]) for entry in command_log) + "\n", encoding="utf-8")
    (repro / "tool_versions.txt").write_text("\n".join(f"{name}\t{tool.version or 'not available'}\t{tool.path or ''}" for name, tool in tools.items()) + "\n", encoding="utf-8")
    checksum_lines = ["path\tsha256\tsize_bytes"]
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "reproducibility.zip":
            rel = path.relative_to(root)
            checksum_lines.append(f"{rel}\t{sha256_file(path)}\t{path.stat().st_size}")
    (repro / "checksums.tsv").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    manifest = {
        "project_id": project_id,
        "app": "ReadQraft",
        "app_version": APP_VERSION or __version__,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "mock_mode": use_mock,
        "options": options.model_dump(),
        "samples": [sample.model_dump() for sample in samples],
        "results": results,
    }
    (repro / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (repro / "methods.txt").write_text(results["methods_text"] + "\n", encoding="utf-8")
    (repro / "session_info.txt").write_text(f"OS/platform: {platform.platform()}\nPython: {platform.python_version()}\nReadQraft: {APP_VERSION}\n", encoding="utf-8")
    (root / "logs" / "commands.json").write_text(json.dumps(command_log, indent=2), encoding="utf-8")


def _zip_reproducibility(root: Path) -> Path:
    zip_path = ensure_within_directory(root, root / "reproducibility.zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for folder_name in ["reproducibility", "logs", "reports", "multiqc"]:
            folder = root / folder_name
            if folder.exists():
                for path in folder.rglob("*"):
                    if path.is_file():
                        archive.write(path, path.relative_to(root))
    return zip_path


def project_results(project_id: str) -> dict[str, Any]:
    root = project_root(project_id)
    state = read_project_state(project_id)
    results = state.get("results", {})
    reports = []
    for folder in ["reports", "multiqc", "qc_raw", "qc_trimmed"]:
        for path in sorted((root / folder).glob("*.html")):
            reports.append({"name": path.name, "url": f"/api/projects/{project_id}/reports/{folder}/{path.name}"})
    methods_path = root / "reproducibility" / "methods.txt"
    return {
        "project_id": project_id,
        "status": state.get("status", "unknown"),
        "samples": results.get("samples", []),
        "reports": reports,
        "downloads": {
            "reproducibility_zip": f"/api/projects/{project_id}/download",
            "methods_text": f"/api/projects/{project_id}/files/reproducibility/methods.txt",
            "command_log": f"/api/projects/{project_id}/files/reproducibility/commands.txt",
            "version_log": f"/api/projects/{project_id}/files/reproducibility/tool_versions.txt",
        },
        "methods_text": methods_path.read_text(encoding="utf-8") if methods_path.exists() else None,
    }
