from app.models.schemas import SampleStatus
from app.services.samples import detect_samples


def test_detect_paired_end_r1_r2():
    samples = detect_samples(["Tumor_R1.fastq.gz", "Tumor_R2.fastq.gz"])
    assert len(samples) == 1
    assert samples[0].sample_id == "Tumor"
    assert samples[0].status == SampleStatus.paired


def test_detect_single_end():
    samples = detect_samples(["SampleA.fastq.gz"])
    assert samples[0].status == SampleStatus.single


def test_missing_pair_flagged():
    samples = detect_samples(["SampleA_R1.fastq.gz"])
    assert samples[0].status == SampleStatus.incomplete
    assert samples[0].warnings
