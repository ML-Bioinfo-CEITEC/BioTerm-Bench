The file `/app/data/region.vcf.gz` is a bgzip-compressed, tabix-indexed
VCF containing a single-sample subset of the GIAB HG002 truth set
covering a slice of chromosome 22.

Produce one output file:

- `/app/output/summary.json` — a UTF-8 JSON object with exactly these
  keys and value types:

      {
        "n_records":  <int>,    // total ALT records (one per line)
        "n_snps":     <int>,    // SNV records (REF and ALT both length 1)
        "n_indels":   <int>,    // records where len(REF) != len(ALT)
        "ti_tv":      <float>,  // transitions / transversions among SNVs
        "het_hom":    <float>   // heterozygous / homozygous genotypes
                                 // across the single sample; count only
                                 // 0/1, 1/0, 1/1 and 0|1, 1|0, 1|1.
      }

Integer counts must be exact. The two ratios must be within 1% of the
reference value. A JSON object with correct keys, types, and values is
required; trailing whitespace/newline is OK.
