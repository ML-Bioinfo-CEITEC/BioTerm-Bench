#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output /tmp/mini_align

cp /app/data/ref.fa /tmp/mini_align/ref.fa
cp /app/data/ref.fa.fai /tmp/mini_align/ref.fa.fai

minimap2 -ax sr /tmp/mini_align/ref.fa \
    /app/data/reads_1.fastq.gz /app/data/reads_2.fastq.gz \
    | samtools sort -o /tmp/mini_align/aln.bam -
samtools index /tmp/mini_align/aln.bam

bcftools mpileup -Ou -f /tmp/mini_align/ref.fa /tmp/mini_align/aln.bam \
    | bcftools call -mv -Ou \
    | bcftools norm -f /tmp/mini_align/ref.fa -m -any -Oz -o /tmp/mini_align/calls.vcf.gz -

tabix -f -p vcf /tmp/mini_align/calls.vcf.gz

bcftools view -R /app/data/targets.bed \
    -Oz -o /app/output/final.vcf.gz /tmp/mini_align/calls.vcf.gz

tabix -f -p vcf /app/output/final.vcf.gz
