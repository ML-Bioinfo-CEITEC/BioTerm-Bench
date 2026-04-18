The file `/app/data/region.vcf.gz` is a bgzip-compressed, tabix-indexed
VCF containing a single-sample subset of the GIAB HG002 truth set
covering a slice of chromosome 22.

Produce one output file:

- `/app/output/summary.json` — a UTF-8 JSON object with exactly these
  keys and value types:

      {
        "n_records":  <int>,    // one count per ALT allele; a row
                                //   with k ALTs contributes k
        "n_snps":     <int>,    // ALT alleles where REF and the ALT
                                //   both have length 1
        "n_indels":   <int>,    // ALT alleles where len(REF) != len(ALT)
        "ti_tv":      <float>,  // transitions / transversions among
                                //   the SNV ALTs
        "het_hom":    <float>   // heterozygous / homozygous genotypes
                                //   of the sole sample, counted once
                                //   per VCF line. Only the patterns
                                //   0/1, 1/0, 1/1, 0|1, 1|0, 1|1 count
                                //   (ignore ./., 0/0, multi-allelic).
      }

Integer counts must be exact. The two ratios must be within 1% of the
reference value. Trailing whitespace/newline is fine.
