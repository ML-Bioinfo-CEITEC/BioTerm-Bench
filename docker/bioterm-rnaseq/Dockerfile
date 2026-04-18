# syntax=docker/dockerfile:1.7
#
# bioterm-rnaseq:v1 -- RNA-seq quantification / DE image.
#
# Derives from bioterm-base. Ubuntu 24.04's arm64 apt ships STAR, subread,
# salmon, and HTSeq at (or within a patch of) the V1 pin targets, so the
# build is shallow and fast.
#
# Installed:
#   - STAR 2.7.11b           (apt: rna-star)
#   - subread 2.0.6          (apt: featureCounts)
#   - salmon 1.10.2          (apt; spec pins 1.10.3; patch-level diff)
#   - HTSeq 2.0.5            (apt: python3-htseq)
#
# Deferred (tracked in docs/status.md):
#   - Prebuilt STAR index for chr22 at /opt/references/chr22/star_index/
#     (~5 GB; generated at task-setup time to keep image size down until
#     count-matrix-from-bams is authored).
ARG BASE_IMAGE=bioterm-base:v1
FROM ${BASE_IMAGE}

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        rna-star \
        subread \
        salmon \
        python3-htseq \
    && rm -rf /var/lib/apt/lists/*

CMD ["/bin/bash"]
