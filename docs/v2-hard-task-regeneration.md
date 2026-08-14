# V2 hard-task regeneration

Run generators from the repository root. They overwrite only the corresponding
candidate's checked-in `data/` and `gold/` fixtures; review those changes before
starting a benchmark run.

```bash
python scripts/generate_bam_splice_junction_support_data.py
python scripts/generate_gtf_reconstruct_translate_data.py
python scripts/generate_vcf_diploid_consensus_data.py
python scripts/generate_vcf_trio_compound_het_data.py
python scripts/generate_vcf_multisample_qc_data.py
python scripts/generate_fastq_paired_adapter_qc_data.py
python scripts/generate_rnaseq_featurecounts_matrix_data.py
python scripts/generate_rnaseq_deseq2_contrast_data.py
python scripts/generate_metagenome_ambiguous_abundance_data.py
python scripts/generate_mini_align_call_filter_data.py
python scripts/generate_kmer_contamination_mixture_data.py
python scripts/generate_ortholog_rbh_clusters_data.py
```

The stochastic generators use the source-level seed `20260812`. The splice,
transcript-reconstruction, diploid-consensus, featureCounts, and metagenomic
generators use fully specified records instead of random sampling. Do not change
either the seed or those literal fixtures after task selection without creating
a new benchmark version and repeating the development-model probe.

After regeneration, validate structure and the independent deterministic
oracles:

```bash
python scripts/validate_task.py
bash scripts/run_oracle_all.sh
```

The selection receipt in `notes/v2_task_selection.json` records which generated
candidates were probed and retained. A full e-INFRA run refuses to start unless
that complete receipt exactly matches `configs/v2_retained_tasks.txt`.
