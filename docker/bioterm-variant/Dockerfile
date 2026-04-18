# syntax=docker/dockerfile:1.7
#
# bioterm-variant:v1 -- Variant calling / annotation / benchmarking image.
#
# Derives from bioterm-base. Current V1 tasks that target this image all
# rely on bcftools (already in base); the extras here prepare for the
# annotation and hap.py-based tasks on the deferred list.
#
# Installed in V1:
#   - SnpEff 5.2.b (apt)     -- annotation, HIGH-impact gene tasks
#
# NOT installed (reason):
#   - vcftools        -- pulls r-cran-ggplot2 which conflicts with the
#                        BioConductor R stack already in bioterm-base.
#   - libvcflib-tools -- same r-cran dep chain. bcftools is the V1 workhorse.
#
# Still TODO (tracked in docs/status.md):
#   - freebayes 1.3.7        -- no arm64 apt package; source build required
#   - VEP 112 + chr22 cache  -- large, needs offline cache provisioning
#   - hap.py 0.3.15          -- Python-2 toolchain makes this painful
#   - rtg-tools vcfeval      -- Java install, pairs with hap.py
ARG BASE_IMAGE=bioterm-base:v1
FROM ${BASE_IMAGE}

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        snpeff \
    && rm -rf /var/lib/apt/lists/*

# Debian's snpeff package installs the launcher at /usr/bin/snpEff (mixed
# case). Provide a lowercase alias for convenience.
RUN ln -sf /usr/bin/snpEff /usr/local/bin/snpeff

CMD ["/bin/bash"]
