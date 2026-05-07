# ReadQraft Tool Strategy

ReadQraft supports bundled or system-installed tools.

Required for real analyses:

- FastQC
- fastp
- MultiQC

Optional advanced engines:

- Cutadapt
- Trimmomatic

The backend checks availability using safe, fixed version commands. The frontend displays missing tools in a friendly Tool Setup panel. Development mock mode is enabled by default for MVP testing and is recorded in reproducibility metadata.

## Local Developer Install

Run:

```bash
npm run tools:install
npm run tools:package
```

This installs a self-contained micromamba environment under `.tools/readqraft-bio` and creates `.tools/readqraft-bio.tar.gz` for Electron packaging. The backend auto-detects that location when launched from the repository, or you can set:

```bash
export READQRAFT_TOOL_ENV="$PWD/.tools/readqraft-bio"
```

For Windows packaging, the GitHub Actions runner runs the same command. Because native Windows fastp packages are not available through Bioconda, Windows bundles Cutadapt as the supported trimming engine. ReadQraft records the actual engine used in each reproducibility package.
