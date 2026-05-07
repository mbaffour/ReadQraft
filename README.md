# ReadQraft

FASTQ QC and trimming without terminal fear.

ReadQraft is a privacy-preserving desktop application for FASTQ/FASTQ.gz read quality control, adapter trimming, quality trimming, post-trim QC, MultiQC reporting, and reproducibility documentation. It is built for biologists who prefer a graphical workflow while preserving proper bioinformatics terminology.

## Who It Is For

ReadQraft is for wet-lab and computational biologists who need a dependable local workflow for:

- FastQC [checks sequencing read quality]
- fastp [adapter trimming and quality trimming]
- MultiQC [combines QC reports into one summary]
- reproducibility ZIPs with commands, versions, checksums, logs, and methods text

## Privacy Statement

Your sequencing reads stay on your computer. The backend binds only to `127.0.0.1` and does not upload FASTQ files to a cloud service.

## MVP Status

This repository contains a working MVP scaffold:

- Electron desktop wrapper starts the local FastAPI backend automatically.
- React frontend detects backend health and tool status.
- FASTQ/FASTQ.gz upload and R1/R2 pairing detection are implemented.
- Simple Mode runs the FastQC -> fastp -> FastQC -> MultiQC pipeline when tools are available.
- Development mock mode is clearly labeled when required tools are missing.
- Progress streams through Server-Sent Events.
- Reproducibility package generation includes commands, versions, checksums, manifest, methods text, and session info.

## Developer Setup

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Frontend:

```bash
npm install
npm run frontend:dev
```

Desktop development:

```bash
npm run frontend:dev
npm run desktop:dev
```

Run tests:

```bash
PYTHONPATH=backend pytest tests
```

## Tool Setup

For real analyses, install:

- FastQC
- fastp
- MultiQC

Optional future engines:

- Cutadapt
- Trimmomatic

The backend checks tool availability at `/api/tools`. If required tools are missing, the UI shows a Tool Setup panel instead of a terminal error.

For local development on macOS/Linux, you can install the required tools into a project-local environment:

```bash
npm run tools:install
npm run tools:package
```

Packaged desktop builds include `readqraft-bio.tar.gz` as an Electron resource and extract it into the app data folder on first launch. The backend then uses `READQRAFT_TOOL_ENV` automatically.

Tool engine strategy:

- macOS bundles FastQC, fastp, Cutadapt, MultiQC, and OpenJDK. Simple Mode uses fastp by default.
- Windows bundles FastQC, Cutadapt, MultiQC, Python, and OpenJDK. Simple Mode uses Cutadapt when fastp is not available as a native Windows package.
- Methods text, command logs, tool versions, and manifests always record the actual trimming engine used.

## Simple Mode Walkthrough

1. Open ReadQraft.
2. Select FASTQ files [raw sequencing read files].
3. Confirm detected single-end or paired-end reads [R1 and R2 read files from the same sample].
4. Use the Illumina short-read default preset.
5. Click Run.
6. Review progress, reports, and the reproducibility ZIP.

## Advanced Mode Walkthrough

Advanced Mode exposes Phred quality threshold [base-call confidence cutoff], minimum read length [shortest read kept after trimming], adapter sequence [known adapter sequence to remove], poly-G/poly-X trimming, thread count, intermediate file handling, and command preview.

## Outputs

Each project folder contains:

- `raw/`
- `qc_raw/`
- `trimmed/`
- `qc_trimmed/`
- `multiqc/`
- `logs/`
- `reports/`
- `reproducibility/`
- `reproducibility.zip`

## Reproducibility

Every completed analysis writes:

- `reproducibility/commands.txt`
- `reproducibility/tool_versions.txt`
- `reproducibility/checksums.tsv`
- `reproducibility/manifest.json`
- `reproducibility/methods.txt`
- `reproducibility/session_info.txt`

## Packaging

See [docs/packaging.md](docs/packaging.md) for macOS, Windows, PyInstaller, and Electron packaging notes.

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md).
