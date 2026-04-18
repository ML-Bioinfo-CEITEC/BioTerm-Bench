# syntax=docker/dockerfile:1.7
#
# bioterm-variant:v1 -- Variant calling / annotation / benchmarking image.
#
# Derives from bioterm-base and adds freebayes, vcflib, VEP (offline cache
# limited to chr22), SnpEff (GRCh38.99 subset), hap.py, and vcfeval from
# rtg-tools.
#
# Placeholder stub for V1: tool contents will be authored alongside the
# Category 2 tasks (mpileup-call-snps, vcf-filter-quality, vcf-split-by-type,
# variant-call-precision-recall, vcf-annotate-impact). Until then this image
# is a pure passthrough of bioterm-base so the build script wires up cleanly.
ARG BASE_IMAGE=bioterm-base:v1
FROM ${BASE_IMAGE}

# TODO(bioterm-variant): install pinned versions:
#   - freebayes 1.3.7
#   - vcflib 1.0.12
#   - VEP 112 with offline cache limited to chr22
#   - SnpEff 5.2 with GRCh38.99 database (chr22 subset)
#   - hap.py 0.3.15
#   - vcfeval from rtg-tools

CMD ["/bin/bash"]
