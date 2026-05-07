# Troubleshooting

## App Does Not Open

Restart the app. On macOS, check Gatekeeper prompts. On Windows, check Windows Defender or SmartScreen prompts.

## Backend Not Connected

ReadQraft starts a local backend on `127.0.0.1`. If the dashboard shows Backend not available, restart the app. Developers can run `npm run backend:dev` to inspect backend startup errors.

## Tool Missing

FastQC was not found [the app could not locate the quality-check tool]. Open Settings > Tool Setup or install the bundled/system tools. Development mock mode demonstrates the workflow but is not valid for publication analyses.

## FASTQ Pair Not Detected

Use common R1/R2 naming patterns such as `Sample_R1.fastq.gz` and `Sample_R2.fastq.gz`. If an R2 file is missing [paired-end reads require both forward and reverse files], add the matching file or treat the sample as single-end.

## Analysis Failed

Open View technical log. The main UI explains what happened and why it matters; the technical log includes stdout/stderr and return codes.

## Reports Not Opening

Confirm the analysis completed and that report files exist in the project folder. MultiQC requires the `multiqc` command for real reports.

## Large Files Are Slow

Large FASTQ.gz files can take time to checksum, trim, and re-check. Increase thread count [number of CPU cores used] in Advanced Mode if your computer has available cores.

## Windows Security Warning

Unsigned development builds can trigger SmartScreen. Signed installers are documented as future distribution work.

## macOS Gatekeeper Warning

Unsigned development builds can trigger Gatekeeper. Signed and notarized builds require Apple developer certificates and are documented as future distribution work.
