# Roadmap to v1.0 — read this first

> **2026-08-27 superseding status:** the unified 50-task BioTerm-Bench v1.0
> set is frozen. See [`v1.0-freeze.md`](v1.0-freeze.md) and
> `configs/benchmark_v1.0_manifest.json`. Step 1, the Qwen3.8 screen, the
> ten-deployment k=1 matrix, adaptive follow-ups, and pre-freeze Rasch selection
> are complete. The live work begins at final model-panel choice, confirmatory
> rerun, paper/poster rewrite, and release engineering. Historical details below
> remain useful provenance but no longer describe the release task set.

Written 2026-08-14, at the start of PS's week off; **updated 2026-08-24** on
PS's return. Everything below is either a decision PS made, or a loose end from
the August work.

> **2026-08-25 update — read
> [`notes/hard-task-search.md`](hard-task-search.md) before doing anything on
> step 1.**
>
> The task set went from 37 to **64 (63 scored)**: 27 new hard candidates in
> seven batches, all validated, all passing a positive *and* a negative oracle.
> `scripts/candidate_recommendation.py` says **keep 12, cut 15**.
>
> **The ceiling did not move.** DeepSeek V4 Flash Thinking lost **one trial
> across all 27 new tasks**. Seven distinct hypotheses about difficulty were
> tested and six were refuted with data: more filtering rules, named
> algorithms, textbook methods implemented exactly, infeasible-to-brute-force
> scale, several graded deliverables, 250-row outputs, and signposted
> pitfalls. A controlled experiment removing the signposting changed nothing
> (35/36). Eleven of the twelve useful new items discriminate only at the
> *bottom* of the ability range.
>
> **Reinstate `gtf-reconstruct-translate` before writing any new task.** It was
> cut in the v2 round as "0/5 -- too hard", but all three probe models were
> small; `qwen/qwen3.8-27b` scored **3/3** on it tonight. That is perfect
> discrimination, and its grader passes all three checks. The selection *rule*
> was fine; the *panel* was weak-only, so it cut the ceiling. A screening panel
> must span the ability range in both directions — the same night's mirror
> error was judging batches 1--2 "too easy" from two strong models before a
> weak one showed four of the seven discriminate.
>
> The other two never-solved tasks are **under-specified, not hard**.
> `fastq-paired-adapter-qc` (0/12) grades JSON floats by exact equality against
> four-decimal gold while its instruction never mentions rounding — a model
> produced 0.6866823213686682 against gold 0.6867 and failed.
> `mini-align-call-filter` (0/9) names no variant caller or parameters yet
> grades the variant set exactly; three models return the identical
> `extra=1 missing=1`. Fix the spec, or leave them out.
>
> **Five graders in the suite reject correct answers** (numeric fields nudged
> by 1e-9): `vcf-to-tsv` and `seqkit-fasta-stats` in core-25,
> `kmer-contamination-mixture` and `vcf-multisample-qc` in the extension, plus
> `fastq-paired-adapter-qc`. **Two of the four IRT weak items are among them**,
> which is a fixable cause for their low discrimination — fix the graders and
> re-run before retiring either. `scripts/check_grader_tolerant.sh` audits the
> whole suite; all 27 new tasks pass it.
>
> There are now three grader checks and every new task should pass all three.
>
> `qwen/qwen3.8-27b` is in the panel and benchmarked on the whole suite: mean
> reward **0.947**, and **0.985** on the 25-task core. A model that runs on a
> laptop.
>
> Two defects: the missing `docker_network_janitor.sh` (written, ran all
> night), and two graders that shipped with a syntax error and scored 0/6,
> looking exactly like a difficulty result
> (`notes/incident-broken-grader.md` — fixed, and now guarded by a negative
> oracle). The `/gold` mount hole in all 37 pre-existing tasks is still open.


---

## The plan, in order

The four steps depend on each other, so the order matters: fix the tasks, then
fix the models, then re-run everything, then analyse.

### 1. Expand and harden the task set → ~50 tasks

**Done in part on 2026-08-25 (64 tasks). Start from the two discarded hard
tasks, not from writing new ones — see `notes/hard-task-search.md`.**


The suite is saturating and that is now measured, not suspected: 9 of 32 tasks
are solved on every attempt by every model, every task has negative IRT
difficulty, and retiring the one genuinely hard task left four of fourteen
models at a perfect score on the extension.

- Target **~50 tasks**, and v1.0 must include genuinely **harder** tasks, not
  just more of the same.
- Generate candidates by **brainstorming with the most capable models**.
  PS is unsure whether this needs a human in the loop as well — decide when
  you see the first batch. The existing 12-candidate round was model-assisted
  and produced one task that turned out anti-correlated with ability, so some
  human filtering is probably warranted.
- **Screen candidates with 1--3 models, not the whole panel**: one small/fast
  model (is it hopeless for everyone?) plus one or two of the most capable
  (is it trivial for the frontier?). A task that the capable models solve on
  every attempt is not a candidate.
- **Select on discrimination, not pass rate.** This is the lesson from the
  current round: the 10--80% pooled-pass-rate band admitted
  `bam-splice-junction-support`, whose item--total correlation turned out to be
  −0.94. See `notes/paper-claims.md` and the IRT section of the manuscript.
- Four current tasks are weak items (2PL discrimination < 1) and are the next
  candidates for revision or retirement:
  `rnaseq-tpm-top-biotype`, `fasta-6frame-codon-counts`, `vcf-to-tsv`, and
  `kmer-contamination-mixture` — the last of which is in the *extension*.
- `bam-splice-junction-support` is already retired via
  `configs/retired_tasks.txt`; its trials are still on disk. Reverting is one
  line if v1.0 wants a hard ceiling back.

### 1a. Add Qwen3.8-27B as soon as its weights land

PS flagged this on the way out: **Qwen3.8-27B should be in the panel.**

Status as of 2026-08-14 (checked, do not assume): it has **not** shipped. It
was committed for the week of 10 August and slipped; the official ModelScope
page is counting down to **midnight 15 August 2026, 00:00 JST**, and there is
still no repository, model card, or licence file. Verify it actually landed
before planning around it.

Why it matters more than an ordinary addition:

- At 27B it is a **tier A model** — roughly 13--14 GB of weights at four bits,
  so it runs on a workstation, and on a 32 GB laptop. Tier A currently has a
  single occupant (Gemma 4, 31B), which is thin support for the paper's
  claim that workstation-class models already handle most routine work. A
  second, newer tier A entry either strengthens that claim or complicates it,
  and both outcomes are worth having.
- It is the natural model for the **local-execution study** listed under future
  directions (Ollama / LM Studio), which is the one deployment route never
  measured.

Also released in the same family and worth considering for the top of the
panel: **Qwen3.8-Max (2.4T total, A95B active)**, whose weights shipped on
13 August. That is a tier E model needing a multi-node cluster, comparable to
Kimi K3 — include it only if the e-INFRA panel can serve it.

Add both to `configs/einfra_panel.tsv` (or the OpenRouter manifest) with total
and active parameter counts and the served precision, or they will not appear
in the hardware-tier table or Figure 4.

### 2. Add older models — the progress story

Once the task set is frozen at 40--50 tasks, widen the model panel
**backwards in time**.

- Include models from 12, 18, and 24 months ago. Many are no longer served by
  OpenRouter or e-INFRA but are still available as weights.
- The intended message, in PS's words: **what was not possible 24 / 18 / 12
  months ago is now possible — if you have been ignoring AI agents, this is
  when to start paying attention.**
- This also fixes a real weakness in the current draft: every model evaluated
  so far was released within about a year, so model size and release date are
  confounded (ρ = 0.76) and the paper has to say the two cannot be separated
  at n = 8. A wider release window breaks that confound.
- Consider adding a local-execution tier at the same time (Ollama / LM Studio),
  which is already listed as future work in the manuscript and would close the
  one deployment route never measured.

### 3. Re-run everything

Once tasks and models are both fixed, **re-run the whole matrix from scratch**.

Rationale: the current results were collected over three months on two
providers, and there is direct evidence this matters — the same model
(Gemma 4 31B) scored 0.920 on OpenRouter in May and 0.880 on e-INFRA in
August, and one model lost 24 of 32 trials to a provider outage that had
cleared ten hours later. A single synchronous re-run removes the possibility
that a model or the harness simply behaved differently months apart.

Practical notes for that run:
- `scripts/pause_experiments.sh` / `scripts/resume_experiments.sh` handle
  stopping and restarting safely; partial jobs resume rather than restart.
- Keep e-INFRA concurrency at 2 (agreed ceiling). The throttle-down path is
  fixed and tested but the ceiling itself is a provider agreement.
- Run `scripts/docker_network_janitor.sh` alongside, or Docker exhausts its
  network address pool after a few hundred trials and destroys a job. This
  already happened once.

### 4. Analysis

With clean, synchronous data, redo the analysis properly.

- **IRT** is the centrepiece: `scripts/irt_analysis.py` already fits a 2PL and
  reports task difficulty, task discrimination, and model ability on one
  scale. With ~50 tasks and a wider model panel the ability estimates stop
  being noisy and the item parameters get much sharper — PS thinks this could
  be genuinely interesting, and it is the natural way to present both "which
  models are capable" and "which tasks measure anything" at once.
- Everything else regenerates with `bash scripts/refresh_paper_tables.sh`,
  which also rebuilds the figures and the paired-scope macros the manuscript
  cites.

---

## Loose ends from the August work

Things PS asked about or that came up and were never closed.

### Needs PS specifically

- **Funding details.** `paper/main.tex` carries a template sentence with
  `[FUNDING BODY]` and `[GRANT NUMBER]` placeholders in the Acknowledgements.
  The e-INFRA acknowledgement is already in and uses their published wording.
- **Author contributions** were removed from the manuscript on PS's
  instruction; add back only if Frontiers requires it.
- **Release tag.** The repository has no tags, so the paper cannot cite a
  version identifier. Cut one before submission.
- **Verify `configs/model_release_dates.tsv`** against vendor model cards. The
  dates came from vendor announcements and press coverage gathered on
  2026-08-13, and the file is marked as needing confirmation.
- **Check the OpenRouter bill** for 12--14 August. Our receipts total
  **$9.43** across 670 trials. If the dashboard disagrees materially, the
  per-model costs are litellm estimates rather than billed prices and the cost
  column (and Figure 3) should come out of the paper. litellm logged
  "model isn't mapped" for all five models yet still reported a price, so this
  is worth one minute of checking.
- **Repository visibility.** Both the paper and the poster state the suite is
  freely available. Confirm the GitHub repo is actually public:
  `gh repo view ML-Bioinfo-CEITEC/BioTerm-Bench --json visibility`.

### Housekeeping

- **The answer key is readable by the agent in all 37 pre-existing tasks.**
  Each mounts `../gold:/gold:ro` into the same container the agent works in.
  Empirically never exploited (1 of 400 trajectories mentions `/gold`, and that
  trial scored 0), but it should not survive into v1.0. Fixing it is not a
  one-line change: the verifier runs in that container too, so each
  `tests/check.py` has to carry its own embedded copy of the expected answer
  first -- the pattern `scripts/hard_candidate_common.py` already uses for the
  16 new tasks. Deliberately not attempted on the night of 24 August because it
  changes every task checksum and a benchmark run was in flight.

- **Delete `.env.swp`** — a Vim swap file in the repo root containing a copy of
  the e-INFRA token. It is now gitignored (`*.swp`) so it will not be
  committed, but it should not exist. `rm .env.swp`.
- **Rotate the e-INFRA token.** The original handoff said to rotate it after
  the experiments; the experiments are finished.
- **`tasks_probe/` and `tasks_probe2/`** are tracked in git and look like
  development leftovers. Prune if they are not needed.

### Manuscript

- **Cut tables.** PS agreed the paper is table-heavy (10 tables, 4 figures).
  The two appendix audit tables are the obvious first cut — excluded
  OpenRouter jobs, and hardest core tasks — since the IRT table now covers
  item quality. That saves about a page.
- **Frontiers fit.** Consider submitting as **Technology and Code** or
  **Methods** rather than Original Research; a released benchmark suite fits
  those better. Section headings are currently essayistic and would need
  renaming for Original Research. Length is not a problem for Frontiers.
- `notes/review-eccb-reader.md` holds a read-through from the perspective of a
  bioinformatician new to AI; most items are applied, the remainder are listed
  there.

### Poster

- **The poster cannot be rebuilt on this machine.** `paper/poster.tex` uses
  `fontspec` with Carlito and Poppins; this machine has no xelatex/lualatex
  and none of those fonts, so even the TeX Gyre Heros fallback fails and
  tectonic errors out. The committed `poster.pdf` is correct and complete —
  it just cannot be regenerated here. Also, its header says `make poster` but
  there is no such target in `paper/Makefile`.
- **The "92%" headline is unqualified.** It is Gemma 4 31B's mean reward on
  the **25-task core, OpenRouter cohort**. The same model scores 0.880 on the
  e-INFRA core and 0.786 on the extension. On the poster it sits beside "32
  tasks" and "14 models evaluated on both parts", which reads as if it were a
  whole-suite figure. Add the scope before the poster is shown again.

---

## Pointers

| What | Where |
|---|---|
| Full operational handoff, incidents, bug write-ups | `notes/TAKEOVER.md` |
| Every verified numerical claim, with provenance | `notes/paper-claims.md` |
| Experiment design, protocol, concurrency policy | `notes/experiment-design.md` |
| Three-perspective paper review | `notes/paper-review-perspectives.md` |
| ECCB-reader review and Frontiers notes | `notes/review-eccb-reader.md` |
| Remaining manuscript to-dos and page budget | `notes/rewrite-todo.md` |
| Literature review and positioning | `notes/literature-review.md` |
| Regenerate every table, figure, and macro | `bash scripts/refresh_paper_tables.sh` |
