# Grading patterns

BioTerm-Bench V1 uses **deterministic grading only**. There are no LLM
judges. Every task's `tests/check.py` must fit one of the five patterns
below. If a task needs something else, redesign the task or cut it.

Each pattern lives in `tests/check.py`, which exits 0 on pass and non-zero
on fail. `tests/test.sh` wraps that exit code into `reward.txt`.

---

## Pattern A: exact file diff (sorted / normalized)

For outputs where the content is fully specified and byte-level equality
(after a defined normalization) is the correct criterion.

```python
import subprocess, sys

cmd = [
    "bash", "-c",
    "diff -q <(sort /app/output/result.tsv) <(sort /gold/result.tsv)",
]
sys.exit(subprocess.call(cmd))
```

Used for: `gtf-to-bed`, `entrez-gene-lookup`, `flagstat-report`.

Tips:

- Always normalize order when sort-order is not part of the task's output
  contract (use `sort`, `sort -k1,1V -k2,2n`, etc.).
- Strip trailing whitespace and CRs when you cannot control the agent's
  text editor output.

---

## Pattern B: set comparison (Jaccard or exact)

For tasks whose output is a set of IDs / items, where the exact count and
order are not the point.

```python
import sys

actual = set(open("/app/output/genes.txt").read().split())
gold   = set(open("/gold/genes.txt").read().split())
denom  = len(actual | gold)
jaccard = (len(actual & gold) / denom) if denom else 0.0
sys.exit(0 if jaccard >= 0.8 else 1)
```

Used for: `deseq2-top-genes`, `vcf-annotate-impact`, `blast-homolog-set`,
`de-and-pathway`, and all four DB-retrieval tasks (see
[live-network-pattern.md](live-network-pattern.md)).

Tips:

- Choose the Jaccard threshold per task (0.8 is a common default for
  "top-N" list tasks; DB tasks may go 0.85–0.9).
- **Do not leak the threshold in `instruction.md`.**

---

## Pattern C: numeric tolerance

For tasks that produce numbers (TPMs, quality scores, summary stats).

```python
import json, sys

actual = json.load(open("/app/output/stats.json"))
gold   = json.load(open("/gold/stats.json"))

for key, gold_val in gold.items():
    if key.endswith("_tol"):
        continue
    tol = gold.get(f"{key}_tol", 0.0)
    if abs(actual[key] - gold_val) > tol:
        sys.exit(1)
sys.exit(0)
```

Used for: `tpm-normalize`, `fastqc-quality-report`, `detect-contamination`,
`vcf-stats-summary`.

Tips:

- Store the tolerance alongside the gold value (`"mean_cov_tol": 0.5`).
  Keeps grading self-contained.
- Use absolute tolerance for counts, relative for quantities spanning
  several orders of magnitude (compute `abs(a - g) / max(1e-9, abs(g))`).

---

## Pattern D: VCF comparison

For variant-output tasks, use `bcftools isec` (filter/split) or `hap.py`
(full calling vs a truth set).

### filter / split tasks

```bash
bcftools isec -p /tmp/isec_out \
    /app/output/filtered.vcf.gz \
    /gold/filtered.vcf.gz
# /tmp/isec_out/README.txt describes 0000-0003 files:
#   0000 = unique to A  (false-positive if agent was supposed to match)
#   0001 = unique to B  (false-negative)
#   0002, 0003 = shared
```

### calling tasks

```bash
hap.py /gold/truth.vcf.gz /app/output/called.vcf.gz \
    -r /opt/references/chr22/chr22.fa.gz \
    -o /tmp/happy_out
# Parse /tmp/happy_out.summary.csv and assert
#   METRIC.Precision >= 0.90  and  METRIC.Recall >= 0.85
```

Used for: `vcf-filter-quality`, `vcf-split-by-type`, `mpileup-call-snps`,
`variant-call-precision-recall`, `call-and-annotate`.

---

## Pattern E: schema + value validation

For tabular outputs with required column structure and per-row checks.

```python
import pandas as pd, sys

df = pd.read_csv("/app/output/result.tsv", sep="\t")

required_cols = {"gene_id", "symbol", "log2FC", "padj"}
if not required_cols.issubset(df.columns):
    sys.exit(1)

if df["padj"].between(0, 1).eq(False).any():
    sys.exit(1)

sys.exit(0)
```

Used for: `batch-effect-flag`, `uniprot-fetch-features`, `multiqc-aggregate`.

Tips:

- Use `pandas` read modes that are tolerant to extra columns / ordering
  differences; enforce only what the task contract requires.
- Keep the check under ~30 lines. If it grows, you're probably trying to
  do LLM-judge-style grading in disguise.

---

## The hard rule

**If your task does not fit one of these five patterns, redesign the task
or cut it from V1.** There are no exceptions. The whole benchmark's value
is that results are reproducible, bit-for-bit, by anyone running it.
