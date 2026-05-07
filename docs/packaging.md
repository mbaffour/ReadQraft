# Packaging

## Backend Sidecar

Build the Python backend executable with PyInstaller:

```bash
cd backend
pip install -r requirements.txt pyinstaller
pyinstaller pyinstaller.spec
```

The Electron build expects the executable under `backend/dist/readqraft-backend`.

## Bioinformatics Tool Bundle

Install and verify FastQC, fastp, MultiQC, and their runtime dependencies:

```bash
npm run tools:install
npm run tools:package
```

This creates:

- `.tools/readqraft-bio`
- `.tools/tools-manifest.json`
- `.tools/readqraft-bio.tar.gz`

Electron copies the archive into app resources and extracts it into the app data folder on first launch. The backend receives `READQRAFT_TOOL_ENV` automatically.

Windows note: Bioconda does not currently provide a native `win-64` fastp package, so the Windows tool bundle installs Cutadapt from PyPI and the backend uses Cutadapt as the Windows-native trimming engine. The actual engine used is recorded in `manifest.json`, `methods.txt`, and command logs.

## Frontend

```bash
npm install
npm run tools:install
npm run tools:package
npm run frontend:build
```

## macOS

```bash
npm run desktop:dist
```

This creates a DMG in `desktop/dist`. Signed and notarized builds require Apple Developer credentials and are future release work.

## Windows

```bash
npm run desktop:dist
```

This creates NSIS and portable targets. Signed installers require a code-signing certificate and are future release work.

## GitHub Actions

Separate macOS and Windows workflows are included under `.github/workflows`.
