# ReadQraft Feature Ideas

This document proposes concrete, incremental features for ReadQraft. Each idea is
scoped against the current MVP scaffold (FastAPI backend + React/Vite frontend +
Electron wrapper) and notes the touch points so the work stays additive and
low-risk. They are ordered roughly by value-to-effort ratio.

## 1. Per-sample QC comparison view

**What:** A results table/grid that shows key FastQC metrics for every sample
side by side (per-base quality mean, %GC, %duplication, adapter content,
overrepresented-sequence count) with a before/after-trimming column pair and a
pass/warn/fail status pill per metric.

**Why:** The current `Results` component (`frontend/src/App.jsx`) only reports
reads before/after and a retention percentage. Biologists comparing many samples
in a run cannot currently spot the one flow cell lane or library that behaved
differently without opening each MultiQC/FastQC HTML report individually. A
compact comparison table is the single most requested view in QC tooling and
turns ReadQraft from "runs the tools" into "helps you interpret the run."

**Touch points:**
- Backend: parse the existing FastQC `fastqc_data.txt` (already produced) into a
  small per-sample metrics dict in `backend/app/pipeline/runner.py`; surface it
  through `ProjectResults.samples` in `backend/app/models/schemas.py`.
- Frontend: extend the `Results` table in `App.jsx` with the new columns and a
  status pill (the `pill ok` / `pill bad` styles already exist).

**Risk:** Low. Purely additive parsing plus presentation; no change to the
command-generation path.

## 2. Adapter auto-detection preview

**What:** Before running the full pipeline, sample the first N reads of each
FASTQ and report the most likely adapter(s) detected (via fastp's
`--detect_adapter_for_pe` dry sampling or a lightweight k-mer scan), showing the
inferred adapter sequence and its abundance in the "Workflow setup" panel.

**Why:** The Advanced-mode "Adapter sequence" field is free text and easy to get
wrong; the app already has `auto_detect_adapters` as a boolean but never tells
the user *what* it detected. Surfacing the detected adapter builds trust and
lets the user confirm or override before committing to a long run. It also pairs
naturally with the new IUPAC validation on `adapter_sequence`.

**Touch points:**
- Backend: a new `POST /api/projects/{id}/detect-adapters` route in
  `backend/app/routes/api.py` returning a per-sample detected-adapter summary.
- Frontend: a "Detect adapters" button in the Advanced `Options` block that fills
  the `adapter_sequence` field (respecting the validator) and shows abundance.

**Risk:** Low–medium. New read-only endpoint; the heavy lifting can reuse fastp
in a fast sampling mode rather than new parsing code.

## 3. MultiQC-style combined report export bundle

**What:** A one-click "Export combined report" that produces a single
self-contained HTML (or PDF) summarizing the whole run — sample table, retention
chart, key QC flags, tool versions, and the methods text — in addition to the
raw MultiQC output already generated.

**Why:** MultiQC output is excellent but assumes familiarity; a portfolio-quality
"share this with your PI" one-pager lowers the barrier for the wet-lab audience
ReadQraft targets. The reproducibility ZIP already collects commands, versions,
checksums, and methods text, so the data needed for a polished report is largely
in hand.

**Touch points:**
- Backend: assemble a templated HTML in `backend/app/pipeline/runner.py` (or a
  new `backend/app/services/report.py`) using the existing methods/version/command
  artifacts; add its path to `ProjectResults.downloads`.
- Frontend: a new download link in the `Results` `downloads` block in `App.jsx`.

**Risk:** Low. Additive artifact; does not alter QC results.

## 4. Drag-and-drop batch folders (recursive sample intake)

**What:** Allow dropping an entire folder (or nested folders) onto the dropzone
and have the backend recursively discover FASTQ/FASTQ.gz files and pair R1/R2
across subdirectories, rather than requiring a flat multi-file selection.

**Why:** Sequencing cores commonly deliver one subfolder per sample. The current
dropzone in `App.jsx` handles `event.dataTransfer.files` (flat file list) and the
picker uses `multiple`, but neither walks a directory tree. Batch-folder intake
removes the most tedious step for real-world multi-sample runs.

**Touch points:**
- Frontend: use the `webkitdirectory` attribute and/or the DataTransferItem
  `webkitGetAsEntry()` traversal in the drop handler in `App.jsx`.
- Backend: the existing pairing detection in `backend/app/services/samples.py`
  needs to tolerate relative subpaths; keep the current `security.py` path
  containment checks.

**Risk:** Medium. Directory traversal must preserve the existing 127.0.0.1-only,
local-path safety guarantees. Gate behind the existing upload validation.

## 5. Resumable / re-runnable runs with per-step caching

**What:** Persist run state so an interrupted or repeated run can skip completed
steps whose inputs are unchanged (e.g., raw FastQC already done), keyed on the
input file checksums that the app already computes.

**Why:** QC + trimming + post-QC + MultiQC over many samples is slow; today a
crash or an app restart means starting over. The app already computes SHA-256
checksums (`backend/app/utils/checksums.py`) and has a project/job model, so a
content-addressed "is this step already done?" check is a natural extension and a
strong reliability story for a portfolio piece.

**Touch points:**
- Backend: record completed-step markers (checksum + options hash) under the
  project directory in `backend/app/pipeline/runner.py`; skip steps on match.
- Frontend: surface "resumed from previous run" in the progress `steps` list in
  `App.jsx`; re-enable the currently-disabled "Open previous analysis" button.

**Risk:** Medium. Correctness hinges on a complete cache key (inputs + all
relevant `RunOptions`); a conservative default of "recompute unless every input
and option matches" keeps it safe. Ship behind an opt-in setting first.

---

### Cross-cutting notes

- Every feature above is additive: none require changing the list-form subprocess
  command construction in `backend/app/pipeline/commands.py`, which keeps the
  security surface stable.
- Features 2 and 4 must continue to honor the local-only, path-containment
  guarantees enforced in `backend/app/security.py`.
- Features 1 and 3 have the best value-to-risk ratio and are the recommended
  starting point.
