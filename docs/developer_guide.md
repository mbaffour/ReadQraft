# Developer Guide

## Architecture

ReadQraft uses:

- Electron desktop wrapper
- React/Vite frontend
- Python FastAPI local backend
- PyInstaller backend sidecar for packaged builds

The backend binds only to `127.0.0.1`. The frontend never sends arbitrary shell commands. The backend constructs whitelisted subprocess argument arrays for supported tools.

## Backend API

- `GET /api/health`
- `GET /api/tools`
- `POST /api/projects`
- `POST /api/projects/{project_id}/files`
- `POST /api/projects/{project_id}/run`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/events`
- `POST /api/jobs/{job_id}/cancel`
- `GET /api/projects/{project_id}/results`
- `GET /api/projects/{project_id}/download`

## Data Layout

Projects are stored under `~/.readqraft/projects` by default. Set `READQRAFT_DATA_DIR` to override this in development.

## Mock Mode

`READQRAFT_ALLOW_MOCK_TOOLS=1` allows development without FastQC, fastp, and MultiQC installed. Mock mode is recorded in `manifest.json`.
