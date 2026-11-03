#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
from __future__ import annotations
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

PY
