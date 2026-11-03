#!/usr/bin/env python3
"""Generate 52 IRT-screening candidates in 13 capability families.

The four variants in each family deliberately provide screening breadth, not
52 claims of item independence.  Later selection should retain at most one
variant per family unless residual-dependence diagnostics justify otherwise.

Usage:
    docker run --rm -v "$PWD":/repo -w /repo bioterm-base:v1 \
        python3 scripts/generate_irt_candidates_batch8.py
"""

from __future__ import annotations

import json
import math
import os
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hard_candidate_common import write_task

ENGINE = r'''from __future__ import annotations
import json, math, os, statistics
from collections import Counter, defaultdict
from pathlib import Path

D = Path(os.environ.get("DATA_DIR", "/app/data"))
O = Path(os.environ.get("OUTPUT_DIR", "/app/output"))
C = json.loads((D / "case.json").read_text())

def revcomp(s):
    return s.translate(str.maketrans("ACGT", "TGCA"))[::-1]

def median(xs):
    return statistics.median(xs)

def emit(header, rows):
    O.mkdir(parents=True, exist_ok=True)
    with (O / "result.tsv").open("w") as f:
        f.write("\t".join(header) + "\n")
        for row in rows:
            f.write("\t".join(str(x) for x in row) + "\n")

op = C["operation"]

if op == "gc_windows":
    rows = []
    w, step, floor = C["window"], C["step"], C["min_gc"]
    for rec in C["sequences"]:
        s = rec["sequence"]
        for start in range(0, len(s) - w + 1, step):
            z = s[start:start+w]; gc = (z.count("G") + z.count("C")) / w
            if gc + 1e-15 >= floor:
                denom = z.count("G") + z.count("C")
                skew = 0 if not denom else (z.count("G") - z.count("C")) / denom
                rows.append((rec["id"], start + 1, start + w, f"{gc:.6f}", f"{skew:.6f}"))
    emit(["seq_id","start_1based","end_1based","gc_fraction","gc_skew"], rows)

elif op == "canonical_kmers":
    k, minimum = C["k"], C["minimum_count"]
    counts = Counter()
    for s in C["sequences"]:
        seq = s["sequence"]
        for i in range(len(seq)-k+1):
            x = seq[i:i+k]
            if set(x) <= set("ACGT"):
                counts[min(x, revcomp(x))] += 1
    rows = [(x,n) for x,n in counts.items() if n >= minimum]
    rows.sort(key=lambda x: (-x[1], x[0]))
    emit(["canonical_kmer","count"], rows)

elif op == "motif_pwm":
    pwm, threshold = C["pwm"], C["threshold"]
    L = len(pwm); rows = []
    for rec in C["sequences"]:
        for strand, seq in (("+", rec["sequence"]), ("-", revcomp(rec["sequence"]))):
            for i in range(len(seq)-L+1):
                z = seq[i:i+L]
                score = sum(math.log2(pwm[j][b] / 0.25) for j,b in enumerate(z))
                if score + 1e-12 >= threshold:
                    start = i + 1 if strand == "+" else len(seq) - i - L + 1
                    rows.append((rec["id"], start, strand, z if strand == "+" else revcomp(z), f"{score:.6f}"))
    rows.sort(key=lambda x: (x[0], x[1], x[2]))
    emit(["seq_id","start_1based","strand","forward_sequence","log2_score"], rows)

elif op == "interval_union":
    by = defaultdict(list)
    for r in C["intervals"]: by[r[0]].append((r[1],r[2]))
    rows = []
    for group in sorted(by):
        merged = []
        for s,e in sorted(by[group]):
            if merged and s <= merged[-1][1] + C["max_gap"] + 1:
                merged[-1][1] = max(merged[-1][1], e)
            else: merged.append([s,e])
        raw = sum(e-s for s,e in by[group]); union = sum(e-s for s,e in merged)
        rows.append((group,len(by[group]),len(merged),raw,union,raw-union))
    emit(["group","input_intervals","merged_blocks","raw_length","union_length","duplicated_length"], rows)

elif op == "reciprocal_overlap":
    rows = []
    for a in C["a"]:
        for b in C["b"]:
            if a[1] != b[1]: continue
            ov = max(0, min(a[3],b[3])-max(a[2],b[2]))
            if ov and ov/(a[3]-a[2]) >= C["fraction"] and ov/(b[3]-b[2]) >= C["fraction"]:
                rows.append((a[0],b[0],ov,f"{ov/(a[3]-a[2]):.6f}",f"{ov/(b[3]-b[2]):.6f}"))
    rows.sort()
    emit(["a_id","b_id","overlap_bp","a_fraction","b_fraction"], rows)

elif op == "cigar_accounting":
    import re
    rows = []
    for rid,cigar in C["records"]:
        ops = [(int(n),op) for n,op in re.findall(r"(\d+)([MIDNSHP=X])",cigar)]
        ref = sum(n for n,o in ops if o in "MDN=X")
        query = sum(n for n,o in ops if o in "MIS=X")
        aligned = sum(n for n,o in ops if o in "M=X")
        ins = sum(n for n,o in ops if o == "I"); dele = sum(n for n,o in ops if o == "D")
        skip = sum(n for n,o in ops if o == "N"); clip = sum(n for n,o in ops if o in "SH")
        rows.append((rid,cigar,ref,query,aligned,ins,dele,skip,clip))
    emit(["read_id","cigar","reference_span","query_consumed","aligned_bases","inserted_bases","deleted_bases","skipped_bases","clipped_bases"], rows)

elif op == "pileup_consensus":
    rows = []
    for contig,pos,ref,counts in C["sites"]:
        depth = sum(counts.values()); ranked = sorted(counts.items(), key=lambda x:(-x[1],x[0]))
        base,n = ranked[0]; frac = n/depth if depth else 0
        call = base if depth >= C["min_depth"] and frac >= C["min_fraction"] else "N"
        rows.append((contig,pos,ref,depth,call,f"{frac:.6f}",int(call not in ("N",ref))))
    emit(["contig","position","reference","depth","consensus","top_fraction","differs_from_reference"], rows)

elif op == "genotype_qc":
    samples = C["samples"]; rows=[]
    for j,s in enumerate(samples):
        vals=[r[1][j] for r in C["variants"]]; called=[x for x in vals if x != -1]
        het=sum(x==1 for x in called); alt=sum(x for x in called)
        rows.append((s,len(called),len(vals)-len(called),f"{len(called)/len(vals):.6f}",het,f"{het/len(called):.6f}",alt))
    emit(["sample","called","missing","call_rate","heterozygous","heterozygosity","alt_alleles"],rows)

elif op == "ld_r2":
    rows=[]
    for i,(ida,a) in enumerate(C["variants"]):
        for idb,b in C["variants"][i+1:]:
            pairs=[(x,y) for x,y in zip(a,b) if x != -1 and y != -1]
            if len(pairs) < C["min_pairs"]: continue
            xs=[x for x,_ in pairs]; ys=[y for _,y in pairs]; mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
            cov=sum((x-mx)*(y-my) for x,y in pairs); vx=sum((x-mx)**2 for x in xs); vy=sum((y-my)**2 for y in ys)
            r2=0 if not vx or not vy else cov*cov/(vx*vy)
            if r2 + 1e-12 >= C["min_r2"]: rows.append((ida,idb,len(pairs),f"{r2:.6f}"))
    rows.sort(key=lambda x:(-float(x[3]),x[0],x[1]))
    emit(["variant_a","variant_b","paired_samples","r_squared"],rows)

elif op == "hwe_exact":
    def exact(obs_hom1, obs_hets, obs_hom2):
        rare = 2*min(obs_hom1,obs_hom2)+obs_hets; gen=obs_hom1+obs_hom2+obs_hets
        probs=[0.0]*(rare+1); mid=int(rare*(2*gen-rare)/(2*gen)); mid += (mid%2)!=(rare%2)
        probs[mid]=1.0; total=1.0; h=mid
        while h>1:
            probs[h-2]=probs[h]*h*(h-1)/(4*((rare-h)//2+1)*(gen-(rare+h)//2+1)); total+=probs[h-2]; h-=2
        h=mid
        while h<=rare-2:
            probs[h+2]=probs[h]*4*((rare-h)//2)*(gen-(rare+h)//2)/((h+2)*(h+1)); total+=probs[h+2]; h+=2
        probs=[p/total for p in probs]; return min(1.0,sum(p for p in probs if p <= probs[obs_hets]+1e-15))
    rows=[]
    for vid,a,b,h in C["counts"]:
        p=exact(a,h,b); rows.append((vid,a,h,b,2*min(a,b)+h,f"{p:.8f}",int(p<C["alpha"])))
    emit(["variant","hom_ref","heterozygous","hom_alt","minor_allele_count","exact_p","fails_hwe"],rows)

elif op == "deseq_size_factors":
    genes=C["genes"]; samples=C["samples"]; ratios=[[] for _ in samples]
    for _,counts in genes:
        if all(x>0 for x in counts):
            gm=math.exp(sum(math.log(x) for x in counts)/len(counts))
            for j,x in enumerate(counts): ratios[j].append(x/gm)
    factors=[median(x) for x in ratios]; scale=math.exp(sum(math.log(x) for x in factors)/len(factors)); factors=[x/scale for x in factors]
    rows=[]
    for j,s in enumerate(samples):
        vals=[counts[j]/factors[j] for _,counts in genes]
        rows.append((s,len(ratios[j]),f"{factors[j]:.8f}",f"{sum(vals):.4f}",f"{median(vals):.4f}"))
    emit(["sample","genes_used","size_factor","normalized_sum","normalized_median"],rows)

elif op == "taxonomy_lca":
    parent=C["parent"]
    def ancestors(x):
        out=[]
        while x is not None: out.append(x); x=parent.get(x)
        return out
    rows=[]
    for q,hits in C["queries"]:
        best=max(x[1] for x in hits); kept=sorted({x[0] for x in hits if x[1] >= best*C["fraction"]})
        paths=[ancestors(x) for x in kept]; common=set(paths[0]).intersection(*paths[1:])
        lca=min(common,key=lambda x:paths[0].index(x))
        rows.append((q,best,len(kept),lca,C["rank"][lca]))
    emit(["query","best_score","retained_hits","lca_taxon","lca_rank"],rows)

elif op == "umi_adjacency":
    def hd(a,b): return sum(x!=y for x,y in zip(a,b))
    rows=[]
    for gene, raw in C["groups"]:
        counts=dict(raw); assigned={}; roots=[]
        for umi,n in sorted(counts.items(),key=lambda x:(-x[1],x[0])):
            if umi in assigned: continue
            roots.append(umi); assigned[umi]=umi; queue=[umi]
            while queue:
                cur=queue.pop(0)
                for v,m in sorted(counts.items()):
                    if v not in assigned and hd(cur,v)<=C["distance"] and counts[cur] >= C["ratio"]*m-C["offset"]:
                        assigned[v]=umi; queue.append(v)
        for root in roots:
            members=sorted(x for x,r in assigned.items() if r==root)
            rows.append((gene,root,sum(counts[x] for x in members),len(members),",".join(members)))
    emit(["gene","representative_umi","read_count","raw_umis","members"],rows)
else:
    raise SystemExit("unknown operation: "+op)
'''


FAMILIES = {
    "gc-window-skew": ("qc", "gc_windows", "Compute filtered sliding-window GC fraction and GC skew. Windows are 1-based inclusive in the output; only complete windows are considered."),
    "canonical-kmer-counts": ("search", "canonical_kmers", "Count canonical DNA k-mers across all sequences. A canonical k-mer is the lexicographically smaller of the observed k-mer and its reverse complement; discard windows containing non-ACGT symbols."),
    "pwm-bidirectional-scan": ("search", "motif_pwm", "Scan every sequence on both strands with the supplied position-weight matrix. Use log2(P(base)/0.25), report hits at or above the threshold, and express reverse hits at their forward-reference start."),
    "grouped-interval-union": ("metadata", "interval_union", "Merge zero-based half-open intervals independently by group. Merge overlapping intervals and intervals separated by no more than max_gap bases; compute raw and union lengths."),
    "reciprocal-interval-overlap": ("metadata", "reciprocal_overlap", "Report interval pairs on the same contig whose half-open overlap covers at least the required fraction of each interval. Boundary touching alone has zero overlap."),
    "cigar-consumption-ledger": ("alignment", "cigar_accounting", "Parse each SAM CIGAR and separately total reference span, query consumption, aligned bases, insertions, deletions, reference skips, and soft plus hard clipping."),
    "pileup-threshold-consensus": ("alignment", "pileup_consensus", "Call the most frequent base at each pileup site only when minimum depth and top-base fraction are met; otherwise call N. Break count ties alphabetically. Encode differs_from_reference as 1 only for a called A/C/G/T base unequal to the reference; an N call is 0."),
    "genotype-sample-qc": ("variant", "genotype_qc", "From diploid alternate-allele dosages (0, 1, 2; -1 missing), compute per-sample call rate, heterozygosity among called genotypes, and total alternate alleles."),
    "pairwise-ld-r2": ("variant", "ld_r2", "For every variant pair, use samples called at both sites and compute squared Pearson correlation of diploid dosages. Keep pairs meeting both the sample-count and r-squared thresholds."),
    "hwe-exact-test": ("variant", "hwe_exact", "Compute the two-sided exact Hardy-Weinberg p-value conditional on minor-allele count, summing genotype configurations whose probability is no greater than the observed configuration. Encode fails_hwe as 1 or 0."),
    "deseq-median-ratio": ("rnaseq", "deseq_size_factors", "For each gene positive in every sample, take the geometric mean across samples and form count/geometric-mean ratios. Each sample's raw size factor is the ordinary median of its ratios (average the middle two when even). Divide all raw factors by their geometric mean. Normalize every gene, including zero-containing genes, as count/size-factor. genes_used is the number of positive-in-every-sample genes; normalized_sum and normalized_median summarize all normalized genes."),
    "taxonomy-score-lca": ("search", "taxonomy_lca", "Keep hits scoring at least the configured fraction of each query's best score, deduplicate their taxa, and report their lowest common ancestor in the supplied taxonomy."),
    "umi-directed-adjacency": ("qc", "umi_adjacency", "Process each gene independently. Visit unassigned roots by decreasing raw read count, breaking ties by UMI. Breadth-first from each root, visit candidate children lexicographically; assign an unassigned child when its Hamming distance from the current parent is at most distance and parent_count >= ratio*child_count-offset. Assigned children can recruit transitively and the first assignment wins. Report representative_umi as the root, read_count as the cluster count sum, raw_umis as its member count, and members as lexicographically sorted UMIs joined by commas."),
}

ORDERS = {
    "gc_windows": "input sequence order, then increasing window start",
    "canonical_kmers": "decreasing count, then canonical k-mer alphabetically",
    "motif_pwm": "sequence ID, start, then strand, all ascending",
    "interval_union": "group alphabetically",
    "reciprocal_overlap": "A interval ID, then B interval ID, alphabetically",
    "cigar_accounting": "input record order",
    "pileup_consensus": "input site order",
    "genotype_qc": "input sample order",
    "ld_r2": "decreasing r-squared, then variant A and variant B alphabetically",
    "hwe_exact": "input variant order",
    "deseq_size_factors": "input sample order",
    "taxonomy_lca": "input query order",
    "umi_adjacency": "input gene order; within a gene, decreasing representative count then UMI alphabetically",
}

SCHEMAS = {
    "gc_windows": "sequences: objects with id and sequence",
    "canonical_kmers": "sequences: objects with id and sequence",
    "motif_pwm": "pwm: list of per-position base-probability objects; sequences: objects with id and sequence",
    "interval_union": "intervals: [group, start_0based, end_0based_exclusive]",
    "reciprocal_overlap": "a and b: [interval_id, contig, start_0based, end_0based_exclusive]",
    "cigar_accounting": "records: [read_id, cigar]",
    "pileup_consensus": "sites: [contig, position_1based, reference_base, {base: count}]",
    "genotype_qc": "variants: [variant_id, dosage_per_sample]; dosage order matches samples",
    "ld_r2": "variants: [variant_id, dosage_per_sample]; -1 is missing",
    "hwe_exact": "counts: [variant_id, hom_ref_count, hom_alt_count, heterozygous_count]",
    "deseq_size_factors": "genes: [gene_id, count_per_sample]; count order matches samples",
    "taxonomy_lca": "parent: taxon to parent; rank: taxon to rank; queries: [query_id, [[taxon, score], ...]]",
    "umi_adjacency": "groups: [gene, [[umi, read_count], ...]]",
}


def dna(rng: random.Random, n: int, gc: float = 0.5) -> str:
    return "".join(rng.choices("ACGT", weights=[1-gc, gc, gc, 1-gc], k=n))


def make_case(operation: str, level: int, rng: random.Random) -> dict:
    if operation == "gc_windows":
        return {"operation":operation,"window":31+10*level,"step":7-level,"min_gc":0.45+0.03*level,
                "sequences":[{"id":f"ctg{i}","sequence":dna(rng,260+40*level,rng.uniform(.25,.75))} for i in range(1,5+level)]}
    if operation == "canonical_kmers":
        seqs=[{"id":f"s{i}","sequence":dna(rng,180+level*40)} for i in range(1,5+level)]
        motif=dna(rng,11+2*level); seqs[0]["sequence"] += motif*level; seqs[1]["sequence"] += revcomp_local(motif)*level
        return {"operation":operation,"k":7+2*level,"minimum_count":2,"sequences":seqs}
    if operation == "motif_pwm":
        L=5+level; consensus=dna(rng,L); pwm=[{b:(.82 if b==x else .06) for b in "ACGT"} for x in consensus]
        seqs=[]
        for i in range(1,5+level):
            s=list(dna(rng,180+level*20)); pos=rng.randrange(10,len(s)-L-10); hit=consensus if i%2 else revcomp_local(consensus); s[pos:pos+L]=hit
            seqs.append({"id":f"seq{i}","sequence":"".join(s)})
        return {"operation":operation,"pwm":pwm,"threshold":L*1.2,"sequences":seqs}
    if operation == "interval_union":
        ints=[]
        for g in range(1,8+2*level):
            pos=100*g
            for _ in range(3+level):
                s=pos+rng.randrange(-20,50); e=s+rng.randrange(15,70); ints.append([f"G{g:02d}",s,e]); pos += rng.randrange(5,55)
        return {"operation":operation,"max_gap":level-1,"intervals":ints}
    if operation == "reciprocal_overlap":
        a=[]; b=[]
        for i in range(1,12+4*level):
            s=i*100+rng.randrange(-30,30); a.append([f"A{i:02d}",f"chr{1+i%2}",s,s+rng.randrange(40,120)])
            t=s+rng.randrange(-50,80); b.append([f"B{i:02d}",f"chr{1+i%2}",t,t+rng.randrange(40,130)])
        return {"operation":operation,"fraction":.3+.1*level,"a":a,"b":b}
    if operation == "cigar_accounting":
        ops="MIDNSHP=X"; records=[]
        for i in range(1,15+5*level):
            chosen=[rng.choice(ops) for _ in range(3+level)]; chosen[0]="M"; records.append([f"read{i:03d}","".join(f"{rng.randrange(1,25)}{o}" for o in chosen)])
        return {"operation":operation,"records":records}
    if operation == "pileup_consensus":
        sites=[]
        for i in range(1,25+10*level):
            ref=rng.choice("ACGT"); counts={b:rng.randrange(0,10+5*level) for b in "ACGT"}; sites.append(["chr1",i*7,ref,counts])
        return {"operation":operation,"min_depth":8+3*level,"min_fraction":.35+.05*level,"sites":sites}
    if operation == "genotype_qc":
        ns=6+2*level; nv=25+15*level; samples=[f"S{i:02d}" for i in range(1,ns+1)]
        variants=[[f"v{i:03d}",[rng.choices([-1,0,1,2],[.05*level,.55,.3,.1])[0] for _ in samples]] for i in range(1,nv+1)]
        return {"operation":operation,"samples":samples,"variants":variants}
    if operation == "ld_r2":
        ns=18+6*level; nv=7+2*level; base=[rng.choice([0,0,1,1,2]) for _ in range(ns)]; vars=[]
        for i in range(nv):
            vals=[(-1 if rng.random()<.03*level else (x if rng.random()<.65 else rng.choice([0,1,2]))) for x in base]
            vars.append([f"v{i+1:02d}",vals])
        return {"operation":operation,"min_pairs":12,"min_r2":.12+.05*level,"variants":vars}
    if operation == "hwe_exact":
        counts=[]
        for i in range(1,12+5*level):
            n=30+10*level; p=rng.uniform(.05,.5); a=sum(rng.random()<(1-p)**2 for _ in range(n)); h=sum(rng.random()<2*p*(1-p) for _ in range(n-a)); b=max(0,n-a-h)
            counts.append([f"v{i:03d}",a,b,h])
        return {"operation":operation,"alpha":.05,"counts":counts}
    if operation == "deseq_size_factors":
        ns=4+level; scales=[math.exp(rng.uniform(-1,1)) for _ in range(ns)]; genes=[]
        for i in range(1,35+15*level):
            base=rng.randrange(5,500); vals=[max(0,int(base*s*rng.uniform(.7,1.3))) for s in scales]
            if i%(13-level)==0: vals[rng.randrange(ns)]=0
            genes.append([f"g{i:03d}",vals])
        return {"operation":operation,"samples":[f"S{i+1}" for i in range(ns)],"genes":genes}
    if operation == "taxonomy_lca":
        parent={"root":None}; rank={"root":"root"}; leaves=[]
        for p in range(1,4+level):
            ph=f"P{p}"; parent[ph]="root"; rank[ph]="phylum"
            for g in range(1,4):
                ge=f"{ph}G{g}"; parent[ge]=ph; rank[ge]="genus"
                for s in range(1,4): leaf=f"{ge}S{s}"; parent[leaf]=ge; rank[leaf]="species"; leaves.append(leaf)
        queries=[]
        for q in range(1,10+4*level):
            chosen=rng.sample(leaves,4+level); queries.append([f"q{q:03d}",[[x,rng.randrange(50,101)] for x in chosen]])
        return {"operation":operation,"fraction":.75+.03*level,"parent":parent,"rank":rank,"queries":queries}
    if operation == "umi_adjacency":
        groups=[]
        for g in range(1,7+2*level):
            roots=[dna(rng,6+level) for _ in range(3)]; raw=[]
            for root in roots:
                raw.append([root,rng.randrange(20,60)])
                for _ in range(level+1):
                    x=list(root); j=rng.randrange(len(x)); x[j]=rng.choice([b for b in "ACGT" if b!=x[j]]); raw.append(["".join(x),rng.randrange(1,15)])
            groups.append([f"gene{g:02d}",raw])
        return {"operation":operation,"distance":1,"ratio":2,"offset":1,"groups":groups}
    raise ValueError(operation)


def revcomp_local(s: str) -> str:
    return s.translate(str.maketrans("ACGT", "TGCA"))[::-1]


def instruction_for(name: str, operation: str, contract: str, case: dict) -> str:
    params = ", ".join(f"{k}={v}" for k,v in case.items() if k not in {"operation","sequences","intervals","a","b","records","sites","samples","variants","counts","genes","parent","rank","queries","groups","pwm"})
    return f"""
    `/app/data/case.json` contains the complete input for this candidate and an
    `operation` field equal to `{operation}`. {contract}

    Parameters for this fixture: {params or "all parameters are contained in the input records"}.
    Do not assume records are pre-sorted unless the requested output order says so.

    Write `/app/output/result.tsv`. The exact required header is documented in
    `/app/data/output_header.txt`. Emit rows in this order: {ORDERS[operation]}.
    Numeric output may contain additional precision.
    """


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    manifest = []
    for family_index, (family, (category, operation, contract)) in enumerate(FAMILIES.items(), start=1):
        for level, letter in enumerate("abcd", start=1):
            name = f"{family}-{letter}"
            rng = random.Random(2026082500 + family_index * 10 + level)
            case = make_case(operation, level, rng)
            case["input_schema"] = SCHEMAS[operation]
            work = root / ".omx" / "tmp" / "irt-batch8" / name
            data, output = work / "data", work / "output"
            data.mkdir(parents=True, exist_ok=True); output.mkdir(parents=True, exist_ok=True)
            (data / "case.json").write_text(json.dumps(case, indent=2, sort_keys=True) + "\n")
            env = os.environ.copy(); env.update(DATA_DIR=str(data), OUTPUT_DIR=str(output))
            subprocess.run([sys.executable, "-c", ENGINE], check=True, env=env)
            expected = (output / "result.tsv").read_text()
            header = expected.splitlines()[0]
            task_data = root / "tasks" / name / "data"; task_data.mkdir(parents=True, exist_ok=True)
            (task_data / "case.json").write_text((data / "case.json").read_text())
            (task_data / "output_header.txt").write_text(
                header + "\nRow order: " + ORDERS[operation] + ".\n"
            )
            solve = "#!/usr/bin/env bash\nset -euo pipefail\nmkdir -p /app/output\npython3 - <<'PY'\n" + ENGINE + "\nPY\n"
            write_task(name, category, [family, operation, f"irt-family-{family_index:02d}", f"level-{level}"],
                       instruction_for(name, operation, contract, case), expected, solve,
                       "/app/output/result.tsv", tol=5e-5, rtol=1e-8)
            manifest.append((name,family,level,category,operation,header))
            print(f"  {name}")
    cfg = root / "configs"
    (cfg / "v10_irt_batch8_tasks.txt").write_text("".join(x[0]+"\n" for x in manifest))
    with (cfg / "v10_irt_batch8_manifest.tsv").open("w") as f:
        f.write("task\tfamily\tlevel\tcategory\toperation\toutput_header\n")
        for row in manifest: f.write("\t".join(map(str,row))+"\n")
    print(f"generated {len(manifest)} candidates in {len(FAMILIES)} families")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
