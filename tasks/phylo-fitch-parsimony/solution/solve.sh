#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
seqs, name, buf = {}, None, []
for line in open("/app/data/alignment.fasta"):
    if line.startswith(">"):
        if name:
            seqs[name] = "".join(buf)
        name, buf = line[1:].strip(), []
    else:
        buf.append(line.strip())
if name:
    seqs[name] = "".join(buf)

nw = open("/app/data/tree.newick").read().strip().rstrip(";")
pos = 0


def node():
    global pos
    if nw[pos] == "(":
        pos += 1
        kids = [node()]
        while nw[pos] == ",":
            pos += 1
            kids.append(node())
        pos += 1
        return kids
    start = pos
    while pos < len(nw) and nw[pos] not in ",()":
        pos += 1
    return nw[start:pos]


tree = node()


def fitch(n, i):
    if isinstance(n, str):
        return {seqs[n][i]}, 0
    sets, cost = [], 0
    for kid in n:
        s, c = fitch(kid, i)
        sets.append(s)
        cost += c
    inter = set.intersection(*sets)
    if inter:
        return inter, cost
    return set.union(*sets), cost + 1


n_sites = len(next(iter(seqs.values())))
with open("/app/output/parsimony.tsv", "w") as fh:
    fh.write("site\tn_distinct_bases\tparsimony_score\n")
    for i in range(n_sites):
        _s, cost = fitch(tree, i)
        distinct = len({s[i] for s in seqs.values()})
        fh.write(f"{i + 1}\t{distinct}\t{cost}\n")
PY
