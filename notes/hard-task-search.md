# The v1.0 hard-task search — night of 2026-08-24/25

PS's brief: the suite is saturating, so find genuinely harder tasks before
anyone can call the benchmark solved. Screen with `qwen/qwen3.8-27b` plus one
or two e-INFRA models, seven hours.

**Result: 64 tasks on disk (63 scored), up from 37. 27 new candidates written,
all validated, all oracles passing in both directions. 12 are recommended to
keep, 15 to cut.**

The more useful outcome is a negative one, established across seven
pre-registered attempts to falsify it:

> **The strongest model in the panel completes routine bioinformatics terminal
> work essentially perfectly.** DeepSeek V4 Flash Thinking lost **one trial in
> 27 tasks**. Task complexity, algorithmic depth, input scale, deliverable
> count, output length and deliberate pitfalls all failed to change that.

---

## What the existing suite measures, and why it saturates

Almost all 37 pre-existing tasks have the same shape: *read one file, apply
filtering rules, write one table*. The published error analysis agrees from the
other side — of 319 scored failures, 21.3% produced no output, 35.1% produced
malformed output, 43.6% produced well-formed output with wrong values. Two
thirds of all failure is clerical, not conceptual. That is precisely the skill
modern models have improved at fastest.

## Seven hypotheses, tested in order

| # | Batch | Hypothesis: a task is hard when it… | Tasks | Verdict |
|---|---|---|---|---|
| 1–2 | 1, 2 | …has more filtering rules and more decoys | 7 | **no effect** — 25/25 on the first pass |
| 3 | 3 | …requires a named algorithm | 3 | no effect |
| 4 | 4 | …requires a textbook method implemented exactly | 6 | no effect (1 frontier failure) |
| 5 | 5 | …cannot be brute-forced, or has several graded deliverables | 3 | no effect |
| 6 | 6 | …has a long, exacting output where one row fails the trial | 2 | no effect |
| 7 | 7 | …has a plausible shortcut giving a confident wrong answer | 3 | no effect |
| 8 | 7-nohint | …has that shortcut **without being warned about it** | 3 | **no effect** (see below) |

Batch 1–2 deserves emphasis: those seven tasks were a deliberate attempt to
make the *existing* task shape harder, and both a frontier model and a 27B
model solved every one on every attempt. **Writing more tasks like the current
ones does not fix saturation.**

### The hint experiment

Batch 7's tasks each carried a sentence naming the pitfall out loud ("These
are not the same number"). Every model scored 6/6, which left the hypothesis
untested rather than refuted: a warned-about pitfall is a specification.

So round 6 ran a controlled pair. For each of the three tasks, a `-nohint`
twin was generated with **identical fixtures and identical expected answers**
(verified `data=yes gold=yes`), differing only by deletion of that one
paragraph.

**35 of 36 trials passed, and the single failure was on the *hinted* version.**
Removing the warning did not lower the pass rate. The tasks are simply within
these models' competence; the hint was never what made them easy.

## What does discriminate

Twelve tasks separate models, and eleven of them separate only at the *bottom*
of the ability range — `gpt-oss-120b` fails where the other two pass. Exactly
one separates at the top:

- **`hmm-viterbi-segments`** — DeepSeek 2/3. Viterbi over 4000 bases, where
  multiplying probabilities underflows to zero and silently returns a wrong
  path. Its failure was `expected 27 data rows, got 28`: one segment boundary.

Reading the grader diagnoses was worth more than any of my hypotheses. The
failures that do occur are *confident wrong answers* — the number a reasonable
shortcut returns:

    vcf-leftalign-concordance   expected 200 data rows, got 274   (un-normalised)
    counts-fisher-bh-fdr        expected 157 data rows, got 400   (unfiltered)
    hmm-viterbi-segments        expected  27 data rows, got  28   (one boundary)

Of 14 failures: 57% wrong row count, 29% wrong cell value, 7% wrong header,
7% empty output. Note the contrast with the existing suite's 21% no-output
rate — on these tasks models almost always produce *something*, and it is
almost always the wrong shape rather than nothing.

## Two never-solved tasks — and why a 0% pass rate is a red flag, not a prize

`scripts/full_bench_report.py` surfaced four tasks that sit in `tasks/` but in
no scored cohort, leftovers from the v2 candidate round. Two have never been
solved by any model:

| task | record | reference solution |
|---|---|---|
| `fastq-paired-adapter-qc` | 0 / 12 across five models | passes |
| `mini-align-call-filter` | 0 / 9 across four models | passes |
| `gtf-reconstruct-translate` | 2 / 7 | passes |
| `metagenome-ambiguous-abundance` | 8 / 8 | passes |

My first reading was that the suite had discarded its own ceiling. **That was
wrong, and it is worth recording why**, because the mistake is the same one the
whole night was about: treating a score as evidence without checking that the
task measures what it claims to.

**`fastq-paired-adapter-qc` is under-specified.** Its grader parses both JSON
files and tests `actual != gold` — exact equality. The gold values are rounded
to four decimals; the instruction never uses the words round, decimal or
precision. A probe model computed

    model  0.6866823213686682
    gold   0.6867

which is *correct to every digit it was asked for*, and failed. Five models,
twelve trials, all failing on an unstated formatting convention.

**`mini-align-call-filter` is under-specified more mildly.** It says "align the
reads, call small variants, left-align and normalize" without pinning the
caller, its parameters or the ploidy model, then grades the variant set
*exactly*. Three independent models return the identical near miss,
`extra=1 missing=1`: one variant where a reasonable caller choice differs from
whatever the reference pipeline did. That is a specification gap, not
difficulty — and it is the fixable one of the two.

So for those two the `[0.10, 0.80]` pass-rate rule did its job: its 0.10 floor
exists to catch ambiguous tasks, and both of these were ambiguous.

**But the third rejected task tells the opposite story.**
`gtf-reconstruct-translate` was rejected as "0/5 scored passes -- too hard".
Tonight `qwen/qwen3.8-27b` scored **3/3** on it:

| panel | record |
|---|---|
| 2026 selection probe (gemma4-26b-a4b, gpt-oss-20b, qwen3-14b) | 0 / 5 |
| qwen3.8-27b, tonight | **3 / 3** |

That is not a task that is too hard. That is a task with **perfect
discrimination** -- no weak model passes it, the stronger model always does --
and it is the single most valuable item shape the suite can contain. Its
grader passes all three checks. **Reinstate it.**

The rule was not what failed; the **panel** was. All three probe models were
small, so every task above their ability looked "too hard" and was cut. That is
exactly the error of this night in mirror image: screening batches 1--2 against
two strong models made seven tasks look "too easy" until a weak model showed
four of them discriminate.

> **A screening panel must span the ability range in both directions.** A
> weak-only panel cuts your ceiling; a strong-only panel cuts your floor. The
> v2 selection used three weak models and lost a perfectly discriminating item.

Re-examining all four rejects with every trial now on disk:

| task | 2026 verdict | all data | now |
|---|---|---|---|
| `gtf-reconstruct-translate` | 0/5 too hard | 3/8 | **reinstate** -- discriminates perfectly |
| `fastq-paired-adapter-qc` | 0/6 too hard | 0/12 | leave out -- grader is brittle |
| `mini-align-call-filter` | 0/6 too hard | 0/9 | fix the spec first -- caller unpinned |
| `metagenome-ambiguous-abundance` | 5/5 too easy | 8/8 | correctly dropped |

The generalisable lesson stands, with a caveat: **a 0% pass rate is more often
an unfair task than a hard one** -- two of three here -- but it is not always,
and the way to tell them apart is to re-screen against a stronger model, not to
inspect the pass rate again.

### A third check is needed

`check_oracle.sh` proves a grader accepts the reference answer.
`check_grader_rejects.sh` proves it rejects a corrupted one. Neither proves it
accepts a **correct answer expressed differently** — unrounded floats, another
JSON key order, trailing whitespace, a different but equivalent VCF record.
That is precisely the hole both tasks fell through, and it is the single most
valuable guard still missing. Sketch:

    for each task: take the gold answer, re-render it in a plausible
    alternative formatting, and require check.py to still pass.

Every new task in this repository should pass all three before it is screened.

## Five graders in the suite reject correct answers

Building the third check (below) turned up a defect worth more than any task I
wrote tonight. Perturbing every numeric field by a relative **1e-9** -- far
below any rounding any task specifies -- and asking whether the grader still
passes:

| task | cohort | |
|---|---|---|
| `vcf-to-tsv` | **core-25** | also an IRT weak item (2PL discrimination < 1) |
| `kmer-contamination-mixture` | **extension** | also an IRT weak item |
| `seqkit-fasta-stats` | **core-25** | |
| `vcf-multisample-qc` | **extension** | |
| `fastq-paired-adapter-qc` | unscored candidate | the 0/12 task |

Suite-wide: 25 tolerant, 34 with no float field to test, **5 brittle**, 0 errors.
All 27 new tasks are tolerant -- the scaffold compares numerically with an
explicit per-task tolerance.

**Two of the four tasks the IRT analysis flagged as weak items have brittle
graders.** That is a mechanism rather than a coincidence: a grader that fails
correct-but-differently-formatted answers injects noise uncorrelated with
ability, which is precisely what low discrimination looks like. The manuscript
currently lists those four for revision or retirement on statistical grounds
alone; for two of them there is now a concrete and fixable cause. Fix the
graders and re-run before retiring either.

## Three oracles, not one

| check | proves |
|---|---|
| `scripts/check_oracle.sh` | the grader **accepts** the reference answer |
| `scripts/check_grader_rejects.sh` | the grader **rejects** a corrupted answer |
| `scripts/check_grader_tolerant.sh` | the grader **accepts** a correct answer formatted differently |

A grader that always passes fails the second. One that always fails passes the
second and fails the first. One that grades formatting instead of substance
passes both and fails the third. All three failure modes occurred in this
single session, which is why all three checks should stay.

## Recommendation

`python3 scripts/candidate_recommendation.py` regenerates this. **Keep 12, cut
15.** The 15 cuts are not wasted: they are the evidence for the negative
result, and they should stay in the repository as such.

Before v1.0, the honest options are:
1. Accept that the ceiling is real and reposition the paper around
   **reliability** (the all-attempts metric) and the **lower half** of the
   ability range, which is where deployment decisions actually get made.
2. Add tasks whose difficulty is not knowledge but **environment** — flaky
   tools, ambiguous real-world inputs, multi-hour pipelines. That is a
   different benchmark and a much larger build.
3. Widen the model panel **downwards and backwards** (already step 2 of the
   roadmap). With 11 of 12 useful items discriminating at the bottom, a panel
   with more weak models extracts far more signal from what already exists.

## Defects found and fixed

**`scripts/docker_network_janitor.sh` did not exist.** `notes/ROADMAP.md` and
both pause/resume scripts referenced it, and the incident it was meant to
prevent — Docker exhausting its ~31-network pool and destroying a running job —
had no guard at all. Written; ran all night; networks stayed at 6–8.

**Two graders shipped with a syntax error**, scoring 0/6 and looking exactly
like a difficulty result. See `notes/incident-broken-grader.md`. Fixed, and
guarded by two new checks: every `tasks/*/tests/check.py` is syntax-checked,
and `scripts/check_grader_rejects.sh` corrupts one number per output file and
requires the grader to fail. All 27 new tasks pass both directions.

**The answer key is readable by the agent in all 37 pre-existing tasks**
(`../gold:/gold:ro` is mounted into the agent's own container). Never exploited
— 1 of 400 trajectories mentions `/gold`, and it scored 0 — but it must not
survive to v1.0. Not fixed tonight: the verifier shares that container, so each
`check.py` needs its own embedded key first. All 27 new tasks are already
clean, using `scripts/hard_candidate_common.py`.

## Reproducing

    docker run --rm -v "$PWD":/repo -w /repo bioterm-base:v1 \
        python3 scripts/generate_hard_candidates_batch{1..7}.py
    python3 scripts/validate_task.py
    bash scripts/check_oracle.sh <task>...          # accepts the gold answer
    bash scripts/check_grader_rejects.sh <task>...  # rejects a corrupted one
    python3 scripts/hardsearch_status.py            # per-task pass rates
    python3 scripts/failure_reasons.py              # why failures failed
    python3 scripts/candidate_recommendation.py     # keep / cut
