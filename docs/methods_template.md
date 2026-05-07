# Methods Template

Raw FASTQ reads were assessed using FastQC (`{fastqc_version}`). Adapter and quality trimming were performed using `{trimming_engine}` (`{trimming_engine_version}`) with `{adapter_policy}`, a Phred quality threshold of Q`{phred_quality_threshold}`, and a minimum read length of `{minimum_read_length}` bp. Trimmed reads were reassessed using FastQC, and QC summaries were aggregated using MultiQC (`{multiqc_version}`). Tool versions, command-line parameters, logs, and file checksums were recorded for reproducibility.
