from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.config import APP_VERSION
from app.models.schemas import HealthResponse, ProjectResults, RunOptions, RunResponse, UploadResponse
from app.pipeline.runner import job_manager, project_results
from app.security import ensure_within_directory, validate_project_id
from app.services.projects import cleanup_project, create_project, project_root, save_uploads
from app.services.samples import detect_samples
from app.services.tools import check_tools

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(version=APP_VERSION)


@router.get("/tools")
def tools() -> dict:
    items = check_tools()
    required_missing = [tool.name for tool in items if tool.required and not tool.available]
    return {"tools": [tool.model_dump() for tool in items], "required_missing": required_missing}


@router.post("/projects")
def create_new_project() -> dict:
    project_id = f"rq_{uuid.uuid4().hex[:12]}"
    create_project(project_id)
    return {"project_id": project_id}


@router.post("/projects/{project_id}/files", response_model=UploadResponse)
async def upload_files(project_id: str, files: list[UploadFile] = File(...)) -> UploadResponse:
    try:
        validate_project_id(project_id)
        uploaded, warnings = await save_uploads(project_id, files)
        samples = detect_samples([item.filename for item in uploaded])
        return UploadResponse(project_id=project_id, files=uploaded, samples=samples, warnings=warnings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/run", response_model=RunResponse)
async def run_project(project_id: str, options: RunOptions) -> RunResponse:
    try:
        validate_project_id(project_id)
        create_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job_manager.create_job(job_id, project_id, options)
    return RunResponse(job_id=job_id, project_id=project_id, status="queued")


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    status = job_manager.jobs.get(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found.")
    return status.model_dump()


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str) -> StreamingResponse:
    if job_id not in job_manager.queues:
        raise HTTPException(status_code=404, detail="Job not found.")

    async def event_stream():
        queue = job_manager.queues[job_id]
        for event in job_manager.jobs[job_id].events:
            yield f"data: {event.model_dump_json()}\n\n"
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15)
                yield f"data: {event.model_dump_json()}\n\n"
                if event.status in {"complete", "failed", "cancelled"}:
                    break
            except asyncio.TimeoutError:
                yield "event: ping\ndata: {}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict:
    if job_id not in job_manager.jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    job_manager.cancel(job_id)
    return {"status": "cancelling"}


@router.get("/projects/{project_id}/results", response_model=ProjectResults)
def results(project_id: str) -> dict:
    try:
        return project_results(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}/download")
def download_reproducibility(project_id: str) -> FileResponse:
    root = project_root(project_id)
    path = ensure_within_directory(root, root / "reproducibility.zip")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Reproducibility ZIP is not available yet.")
    return FileResponse(path, filename=f"{project_id}_readqraft_reproducibility.zip")


@router.get("/projects/{project_id}/reports/{folder}/{filename}")
def report_file(project_id: str, folder: str, filename: str) -> FileResponse:
    if folder not in {"reports", "multiqc", "qc_raw", "qc_trimmed"}:
        raise HTTPException(status_code=400, detail="Unsupported report folder.")
    root = project_root(project_id)
    path = ensure_within_directory(root, root / folder / Path(filename).name)
    if not path.exists() or path.suffix.lower() != ".html":
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(path, media_type="text/html")


@router.get("/projects/{project_id}/files/{folder}/{filename}")
def project_file(project_id: str, folder: str, filename: str) -> FileResponse:
    if folder not in {"reproducibility", "logs"}:
        raise HTTPException(status_code=400, detail="Unsupported file folder.")
    root = project_root(project_id)
    path = ensure_within_directory(root, root / folder / Path(filename).name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(path)


@router.delete("/projects/{project_id}")
def cleanup(project_id: str) -> dict:
    cleanup_project(project_id)
    return {"status": "deleted"}
