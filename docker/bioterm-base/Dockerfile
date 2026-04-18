# syntax=docker/dockerfile:1.7
#
# bioterm-base:v1 -- Core BioTerm-Bench image.
#
# Ships the HTS stack, QC / search tooling, Python + R bioinformatics stacks,
# NCBI entrez-direct, and the reference bundle under /opt/references.
#
# Target: <3 GB compressed. Native builds for linux/amd64 and linux/arm64.
# Build with:
#   docker buildx build --platform linux/amd64,linux/arm64 \
#       -t bioterm-base:v1 docker/bioterm-base/
FROM ubuntu:24.04

ARG TARGETARCH
ARG DEBIAN_FRONTEND=noninteractive

# ---------------------------------------------------------------------------
# Pinned tool versions. Keep these grouped at the top for easy auditing.
# ---------------------------------------------------------------------------
ARG HTSLIB_VERSION=1.21
ARG SAMTOOLS_VERSION=1.21
ARG BCFTOOLS_VERSION=1.21
ARG BWA_MEM2_VERSION=2.2.1
ARG MINIMAP2_VERSION=2.28
ARG BEDTOOLS_VERSION=2.31.1
ARG SEQKIT_VERSION=2.8.2
ARG FASTQC_VERSION=0.12.1
ARG MULTIQC_VERSION=1.25.1
ARG BLAST_VERSION=2.16.0
ARG MAFFT_VERSION=7.526
ARG JELLYFISH_VERSION=2.3.1
ARG ENSEMBL_RELEASE=112

# ---------------------------------------------------------------------------
# 1. System dependencies
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        cmake \
        curl \
        default-jre-headless \
        gfortran \
        git \
        gnuplot-nox \
        jq \
        libbz2-dev \
        libcurl4-openssl-dev \
        libdeflate-dev \
        liblzma-dev \
        libncurses-dev \
        libssl-dev \
        libxml2-dev \
        libz-dev \
        make \
        perl \
        pkg-config \
        python3 \
        python3-dev \
        python3-pip \
        python3-venv \
        tabix \
        unzip \
        wget \
        xz-utils \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Map Docker TARGETARCH to common arch labels used by upstream releases.
#   amd64 -> x86_64 / linux64
#   arm64 -> aarch64 / arm64
RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64) echo "x86_64"  > /tmp/arch_gnu;  echo "linux64" > /tmp/arch_label ;; \
        arm64) echo "aarch64" > /tmp/arch_gnu;  echo "arm64"   > /tmp/arch_label ;; \
        *) echo "unsupported TARGETARCH=${TARGETARCH}" >&2; exit 1 ;; \
    esac

# ---------------------------------------------------------------------------
# 2. HTS stack (htslib, samtools, bcftools -- compile pinned versions from source)
# ---------------------------------------------------------------------------
RUN set -eux; \
    cd /tmp; \
    wget -q https://github.com/samtools/htslib/releases/download/${HTSLIB_VERSION}/htslib-${HTSLIB_VERSION}.tar.bz2; \
    tar -xjf htslib-${HTSLIB_VERSION}.tar.bz2; \
    cd htslib-${HTSLIB_VERSION}; \
    ./configure --enable-libcurl --enable-s3 --enable-gcs; \
    make -j"$(nproc)"; \
    make install; \
    ldconfig; \
    cd /tmp && rm -rf htslib-${HTSLIB_VERSION}*

RUN set -eux; \
    cd /tmp; \
    wget -q https://github.com/samtools/samtools/releases/download/${SAMTOOLS_VERSION}/samtools-${SAMTOOLS_VERSION}.tar.bz2; \
    tar -xjf samtools-${SAMTOOLS_VERSION}.tar.bz2; \
    cd samtools-${SAMTOOLS_VERSION}; \
    ./configure --with-htslib=system; \
    make -j"$(nproc)"; \
    make install; \
    cd /tmp && rm -rf samtools-${SAMTOOLS_VERSION}*

RUN set -eux; \
    cd /tmp; \
    wget -q https://github.com/samtools/bcftools/releases/download/${BCFTOOLS_VERSION}/bcftools-${BCFTOOLS_VERSION}.tar.bz2; \
    tar -xjf bcftools-${BCFTOOLS_VERSION}.tar.bz2; \
    cd bcftools-${BCFTOOLS_VERSION}; \
    ./configure --with-htslib=system; \
    make -j"$(nproc)"; \
    make install; \
    cd /tmp && rm -rf bcftools-${BCFTOOLS_VERSION}*

# ---------------------------------------------------------------------------
# 3. Aligners
# bwa-mem2 upstream ships an x86_64 binary only. On arm64 we compile from
# source with sse2neon shims (the project's recommended portable build).
# ---------------------------------------------------------------------------
RUN set -eux; \
    cd /opt; \
    if [ "${TARGETARCH}" = "amd64" ]; then \
        wget -q https://github.com/bwa-mem2/bwa-mem2/releases/download/v${BWA_MEM2_VERSION}/bwa-mem2-${BWA_MEM2_VERSION}_x64-linux.tar.bz2; \
        tar -xjf bwa-mem2-${BWA_MEM2_VERSION}_x64-linux.tar.bz2; \
        rm bwa-mem2-${BWA_MEM2_VERSION}_x64-linux.tar.bz2; \
        mv bwa-mem2-${BWA_MEM2_VERSION}_x64-linux bwa-mem2; \
    else \
        git clone --depth 1 --branch v${BWA_MEM2_VERSION} --recursive \
            https://github.com/bwa-mem2/bwa-mem2.git; \
        cd bwa-mem2; \
        make arch=sse41 CXX=g++ -j"$(nproc)" || make -j"$(nproc)"; \
    fi; \
    ln -s /opt/bwa-mem2/bwa-mem2 /usr/local/bin/bwa-mem2

RUN set -eux; \
    cd /tmp; \
    git clone --depth 1 --branch v${MINIMAP2_VERSION} https://github.com/lh3/minimap2.git; \
    cd minimap2; \
    if [ "${TARGETARCH}" = "arm64" ]; then \
        make -j"$(nproc)" arm_neon=1 aarch64=1; \
    else \
        make -j"$(nproc)"; \
    fi; \
    install -m 0755 minimap2 /usr/local/bin/; \
    cd /tmp && rm -rf minimap2

# ---------------------------------------------------------------------------
# 4. Interval/sequence utilities
# ---------------------------------------------------------------------------
RUN set -eux; \
    cd /tmp; \
    wget -q https://github.com/arq5x/bedtools2/releases/download/v${BEDTOOLS_VERSION}/bedtools-${BEDTOOLS_VERSION}.tar.gz; \
    tar -xzf bedtools-${BEDTOOLS_VERSION}.tar.gz; \
    cd bedtools2; \
    make -j"$(nproc)"; \
    install -m 0755 bin/bedtools /usr/local/bin/; \
    cd /tmp && rm -rf bedtools*

RUN set -eux; \
    cd /tmp; \
    ARCH_LABEL="$(cat /tmp/arch_label)"; \
    wget -q "https://github.com/shenwei356/seqkit/releases/download/v${SEQKIT_VERSION}/seqkit_linux_${ARCH_LABEL}.tar.gz"; \
    tar -xzf "seqkit_linux_${ARCH_LABEL}.tar.gz"; \
    install -m 0755 seqkit /usr/local/bin/; \
    rm -f seqkit "seqkit_linux_${ARCH_LABEL}.tar.gz"

# ---------------------------------------------------------------------------
# 5. QC tools (FastQC is JVM-based and arch-independent; MultiQC via pip below)
# ---------------------------------------------------------------------------
RUN set -eux; \
    cd /opt; \
    wget -q https://www.bioinformatics.babraham.ac.uk/projects/fastqc/fastqc_v${FASTQC_VERSION}.zip; \
    unzip -q fastqc_v${FASTQC_VERSION}.zip; \
    rm fastqc_v${FASTQC_VERSION}.zip; \
    chmod +x FastQC/fastqc; \
    ln -s /opt/FastQC/fastqc /usr/local/bin/fastqc

# ---------------------------------------------------------------------------
# 6. Search / MSA / kmer tools
# ---------------------------------------------------------------------------
RUN set -eux; \
    cd /opt; \
    ARCH_GNU="$(cat /tmp/arch_gnu)"; \
    wget -q "https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/${BLAST_VERSION}/ncbi-blast-${BLAST_VERSION}+-${ARCH_GNU}-linux.tar.gz"; \
    tar -xzf "ncbi-blast-${BLAST_VERSION}+-${ARCH_GNU}-linux.tar.gz"; \
    rm "ncbi-blast-${BLAST_VERSION}+-${ARCH_GNU}-linux.tar.gz"; \
    for bin in /opt/ncbi-blast-${BLAST_VERSION}+/bin/*; do \
        ln -s "$bin" "/usr/local/bin/$(basename "$bin")"; \
    done

RUN set -eux; \
    cd /tmp; \
    wget -q "https://mafft.cbrc.jp/alignment/software/mafft-${MAFFT_VERSION}-without-extensions-src.tgz"; \
    tar -xzf "mafft-${MAFFT_VERSION}-without-extensions-src.tgz"; \
    cd mafft-${MAFFT_VERSION}-without-extensions/core; \
    make clean && make -j"$(nproc)" && make install; \
    cd /tmp && rm -rf mafft-${MAFFT_VERSION}*

RUN set -eux; \
    cd /tmp; \
    wget -q "https://github.com/gmarcais/Jellyfish/releases/download/v${JELLYFISH_VERSION}/jellyfish-${JELLYFISH_VERSION}.tar.gz"; \
    tar -xzf "jellyfish-${JELLYFISH_VERSION}.tar.gz"; \
    cd jellyfish-${JELLYFISH_VERSION}; \
    ./configure; make -j"$(nproc)"; make install; ldconfig; \
    cd /tmp && rm -rf jellyfish-${JELLYFISH_VERSION}*

# ---------------------------------------------------------------------------
# 7. NCBI entrez-direct
# ---------------------------------------------------------------------------
RUN set -eux; \
    sh -c "$(curl -fsSL https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect/install-edirect.sh)"; \
    mv /root/edirect /opt/edirect; \
    ln -s /opt/edirect/* /usr/local/bin/ 2>/dev/null || true
ENV PATH="/opt/edirect:${PATH}"

# ---------------------------------------------------------------------------
# 8. Python scientific stack (system interpreter is Python 3.12 on 24.04)
# PEP 668 marks system Python as externally managed; --break-system-packages
# is the supported escape hatch inside a container.
# ---------------------------------------------------------------------------
RUN pip3 install --no-cache-dir --break-system-packages \
        "multiqc==${MULTIQC_VERSION}" \
        "mygene>=3.2" \
        "biopython>=1.83" \
        "pysam>=0.22" \
        "pandas>=2.2" \
        "numpy>=1.26,<2.3" \
        "scipy>=1.13" \
        "requests>=2.32" \
        "click>=8.1" \
        "tenacity>=8.5"

# ---------------------------------------------------------------------------
# 9. R 4.4 + Bioconductor (DESeq2 / edgeR / limma / tximport).
# CRAN Ubuntu 24.04 repo provides R 4.4.x.
# ---------------------------------------------------------------------------
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends software-properties-common dirmngr gpg-agent; \
    wget -qO- https://cloud.r-project.org/bin/linux/ubuntu/marutter_pubkey.asc \
        | gpg --dearmor -o /etc/apt/trusted.gpg.d/cran_ubuntu_key.gpg; \
    echo "deb https://cloud.r-project.org/bin/linux/ubuntu noble-cran40/" \
        > /etc/apt/sources.list.d/cran.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        r-base r-base-dev \
        libxml2-dev libssl-dev libcurl4-openssl-dev \
        libfontconfig1-dev libharfbuzz-dev libfribidi-dev \
        libfreetype6-dev libpng-dev libtiff5-dev libjpeg-dev; \
    rm -rf /var/lib/apt/lists/*; \
    R -q -e 'install.packages("BiocManager", repos="https://cloud.r-project.org")'; \
    R -q -e 'BiocManager::install(c("DESeq2","edgeR","limma","tximport"), ask=FALSE, update=FALSE)'

# ---------------------------------------------------------------------------
# 10. uv for agent-side Python environments
# ---------------------------------------------------------------------------
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

# ---------------------------------------------------------------------------
# 11. Reference bundle under /opt/references
# ---------------------------------------------------------------------------
RUN mkdir -p /opt/references/chr22 /opt/references/giab \
             /opt/references/bacteria /opt/references/virus \
             /opt/references/blast_db

# Human chr22 (GRCh38 primary assembly) + GTF
RUN set -eux; \
    cd /opt/references/chr22; \
    wget -q -O chr22.fa.gz \
        "http://ftp.ensembl.org/pub/release-${ENSEMBL_RELEASE}/fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna.chromosome.22.fa.gz"; \
    # Ensembl ships a .gz; re-bgzip so it's indexable by samtools/htslib.
    zcat chr22.fa.gz | bgzip -@ 4 > chr22.fa.bgz; \
    mv chr22.fa.bgz chr22.fa.gz; \
    samtools faidx chr22.fa.gz; \
    wget -q -O chr22.gtf.gz \
        "http://ftp.ensembl.org/pub/release-${ENSEMBL_RELEASE}/gtf/homo_sapiens/Homo_sapiens.GRCh38.${ENSEMBL_RELEASE}.chromosome.22.gtf.gz"; \
    /opt/bwa-mem2/bwa-mem2 index chr22.fa.gz || bwa-mem2 index chr22.fa.gz

# GIAB HG002 truth set, subset to chr22
RUN set -eux; \
    cd /opt/references/giab; \
    wget -q -O HG002_truth_full.vcf.gz \
        "https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/AshkenazimTrio/HG002_NA24385_son/NISTv4.2.1/GRCh38/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz"; \
    wget -q -O HG002_truth_full.vcf.gz.tbi \
        "https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/AshkenazimTrio/HG002_NA24385_son/NISTv4.2.1/GRCh38/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz.tbi"; \
    bcftools view -r chr22 HG002_truth_full.vcf.gz -O z -o HG002_GRCh38_chr22_truth.vcf.gz; \
    tabix -p vcf HG002_GRCh38_chr22_truth.vcf.gz; \
    rm HG002_truth_full.vcf.gz HG002_truth_full.vcf.gz.tbi

# E. coli K-12 MG1655 (GCF_000005845.2) + BWA index
RUN set -eux; \
    cd /opt/references/bacteria; \
    wget -q -O ecoli_k12.fa.gz \
        "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/005/845/GCF_000005845.2_ASM584v2/GCF_000005845.2_ASM584v2_genomic.fna.gz"; \
    zcat ecoli_k12.fa.gz | bgzip -@ 4 > ecoli_k12.fa.bgz; \
    mv ecoli_k12.fa.bgz ecoli_k12.fa.gz; \
    samtools faidx ecoli_k12.fa.gz; \
    bwa-mem2 index ecoli_k12.fa.gz

# SARS-CoV-2 reference NC_045512.2 (GCF_009858895.2) + BWA index
RUN set -eux; \
    cd /opt/references/virus; \
    wget -q -O sars_cov_2.fa.gz \
        "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/009/858/895/GCF_009858895.2_ASM985889v3/GCF_009858895.2_ASM985889v3_genomic.fna.gz"; \
    zcat sars_cov_2.fa.gz | bgzip -@ 4 > sars_cov_2.fa.bgz; \
    mv sars_cov_2.fa.bgz sars_cov_2.fa.gz; \
    samtools faidx sars_cov_2.fa.gz; \
    bwa-mem2 index sars_cov_2.fa.gz

# Small curated protein BLAST DB (UniProt Swiss-Prot human kinome subset, <100MB).
# Keeps the DB tiny but non-trivial for blastp best-hit / homolog-set tasks.
RUN set -eux; \
    cd /opt/references/blast_db; \
    curl -sS -o kinome.fasta \
        "https://rest.uniprot.org/uniprotkb/stream?query=reviewed:true+AND+organism_id:9606+AND+keyword:KW-0418&format=fasta"; \
    makeblastdb -in kinome.fasta -dbtype prot -out kinome -title "UniProt human kinome (Swiss-Prot)"; \
    rm -f kinome.fasta

ENV BLASTDB=/opt/references/blast_db

# ---------------------------------------------------------------------------
# 12. Harbor boilerplate (tmux + asciinema, workdir)
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        tmux asciinema \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Overridden at runtime by the harness -- lifts NCBI rate limit from 3 to 10 req/s.
ENV NCBI_API_KEY=""

# ---------------------------------------------------------------------------
# 13. Size guard (informational; build log will surface oversize regressions)
# ---------------------------------------------------------------------------
RUN set -eux; \
    echo "=== /opt/references sizes ==="; du -sh /opt/references/*; \
    echo "=== /usr/local size ==="; du -sh /usr/local; \
    echo "=== tool versions ==="; \
    samtools --version | head -1; \
    bcftools --version | head -1; \
    bwa-mem2 version 2>&1 | head -1 || true; \
    minimap2 --version; \
    bedtools --version; \
    seqkit version; \
    fastqc --version; \
    multiqc --version; \
    blastn -version | head -1; \
    mafft --version 2>&1 | head -1 || true; \
    R --version | head -1

CMD ["/bin/bash"]
