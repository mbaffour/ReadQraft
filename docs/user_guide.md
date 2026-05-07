# ReadQraft User Guide

## Dashboard

Screenshot placeholder: dashboard with backend status, New analysis, Open previous analysis, View example workflow, and Settings.

## Selecting FASTQ Files

Use the file picker or drag-and-drop FASTQ files [raw sequencing read files]. ReadQraft detects common paired-end naming patterns including `_R1/_R2`, `_1/_2`, `.R1/.R2`, and forward/reverse.

Screenshot placeholder: upload panel with detected pairing table.

## Simple Mode

Simple Mode uses good defaults for Illumina short-read data:

- raw FastQC [quality check before trimming]
- fastp [adapter and quality trimming]
- Q20 Phred quality threshold [base-call confidence cutoff]
- 50 bp minimum read length [shortest read kept after trimming]
- post-trim FastQC [quality check after trimming]
- MultiQC [combined QC summary]
- reproducibility ZIP

Screenshot placeholder: Simple Mode workflow summary.

## Advanced Mode

Advanced Mode exposes trimming engine, adapter sequence, auto-detect adapters, poly-G trimming, poly-X trimming, thread count, paired-end synchronization, intermediate files, methods text, checksums, and command preview.

Screenshot placeholder: Advanced Mode settings.

## Results

The Results page shows reads before trimming [raw input reads], reads after trimming [retained reads], read retention percentage [percentage of reads kept], report links, and downloads.

Screenshot placeholder: results table and downloads.
