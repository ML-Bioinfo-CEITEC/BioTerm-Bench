# Live-network pattern for DB-retrieval tasks

Four V1 tasks retrieve information from public bioinformatics APIs:

- `entrez-gene-lookup`
- `mygene-properties-query`
- `uniprot-fetch-features`
- `id-resolution-cross-db`

Rather than mocking the network with a recording proxy (which forces the
agent onto exact pre-recorded URLs and fails reasonable variants for the
wrong reason), these tasks use a **whitelisted live-network pattern**
combined with **pre-evaluation gold refresh** and **tolerant grading**.

The rest of the benchmark has no network access. Ever.

## 1. Whitelisted hosts

In `task.toml`:

```toml
[environment]
docker_image  = "bioterm-base:v1"
network       = "restricted"
allowed_hosts = [
    "eutils.ncbi.nlm.nih.gov",
    "www.ncbi.nlm.nih.gov",
    "mygene.info",
    "rest.ensembl.org",
    "rest.uniprot.org",
    "www.uniprot.org",
]
```

If the Harbor version in use does not honour `allowed_hosts` directly,
the equivalent is an iptables pre-hook in the task; see §7.1 of the
project build spec for the snippet.

## 2. NCBI API key

Bake the env var into the base image (value provided at runtime by the
harness):

```dockerfile
ENV NCBI_API_KEY=""
```

With the key, NCBI raises the rate limit from 3 req/s to 10 req/s — plenty
for this benchmark's traffic.

Register a key at <https://www.ncbi.nlm.nih.gov/account/settings/> and
set `NCBI_API_KEY=...` when running `harbor run`.

## 3. Gold-refresh cadence

Before every formal evaluation cycle, regenerate the DB golds against
current upstream state:

```bash
NCBI_API_KEY=... scripts/refresh_db_golds.sh
git add tasks/*/gold
git commit -m "refresh: DB gold sets $(date -u +%Y-%m-%d)"
```

Scores within a cycle (same gold commit) are comparable bit-for-bit.
Cross-cycle comparisons are reported with the gold-refresh commit timestamp.

If a refresh produces a gold set that differs from the previous gold by
more than 15%, flag it for manual review — that is almost always an
upstream structural change worth investigating before accepting.

## 4. Tolerant grading

All four DB tasks use set-tolerant comparison (Pattern B in
[grading-patterns.md](grading-patterns.md)):

| task                          | grader                                                                     |
|-------------------------------|----------------------------------------------------------------------------|
| `entrez-gene-lookup`          | Jaccard ≥ 0.9 on returned rows (tolerates symbol renames)                  |
| `mygene-properties-query`     | Jaccard ≥ 0.85 on returned gene set                                        |
| `uniprot-fetch-features`      | per-protein position-set Jaccard ≥ 0.9                                     |
| `id-resolution-cross-db`      | Jaccard ≥ 0.9 on successful mappings; NA handling evaluated separately     |

Thresholds are chosen to absorb small upstream drift without corrupting
scores. They are **not** revealed in `instruction.md`.

## 5. Grading-side retry

Graders that hit live APIs (e.g. to confirm an agent-returned Ensembl ID
actually exists) retry 3× with exponential backoff:

```python
import time, requests

def fetch_with_retry(url, max_attempts=3, timeout=10):
    for attempt in range(max_attempts):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt == max_attempts - 1:
                raise
            time.sleep(2 ** attempt)
```

Transient API failures during grading do **not** fail the task; they
trigger the retry.

## 6. Offline fallback (optional)

For air-gapped labs, each DB task ships an optional `offline_fixtures/`
directory of pre-fetched response payloads. Setting `BIOTERM_OFFLINE=1`
in the container environment makes a wrapper script (installed in the
base image at `/usr/local/bin/curl`, `efetch`, etc.) serve responses
from fixtures instead of the network.

This is a fallback, not the primary mode. Scores under `BIOTERM_OFFLINE=1`
are reported separately in the leaderboard with an `(offline)` suffix.

## 7. Serialization

To stay under upstream rate limits, run DB tasks **serially** within a
single model run. Do not parallelize four DB tasks against the same
`NCBI_API_KEY`.
