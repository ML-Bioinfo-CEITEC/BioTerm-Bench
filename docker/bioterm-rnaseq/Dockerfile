# syntax=docker/dockerfile:1.7
#
# bioterm-rnaseq:v1 -- RNA-seq quantification / DE image.
#
# Derives from bioterm-base and adds STAR, salmon, subread (featureCounts),
# and HTSeq. Also bakes a prebuilt STAR index for chr22 at
# /opt/references/chr22/star_index/.
#
# Placeholder stub for V1: tool contents will be authored alongside the
# four Category 3 tasks (tpm-normalize, deseq2-top-genes,
# count-matrix-from-bams, batch-effect-flag). Until then this image is a
# pure passthrough of bioterm-base so the build script wires up cleanly.
ARG BASE_IMAGE=bioterm-base:v1
FROM ${BASE_IMAGE}

# TODO(bioterm-rnaseq): install pinned versions:
#   - STAR 2.7.11b
#   - salmon 1.10.3
#   - subread 2.0.6 (featureCounts)
#   - HTSeq 2.0.5
# TODO(bioterm-rnaseq): build STAR index for chr22 at
#   /opt/references/chr22/star_index/

CMD ["/bin/bash"]
