#!/usr/bin/env bash
# Build BioTerm-Bench Docker images with buildx (multi-arch).
#
# Usage:
#   scripts/build_images.sh [--load|--push] [--only base|rnaseq|variant] [--tag TAG]
#
# Defaults:
#   - --load (load into local Docker engine), single-arch = host arch
#   - Tag: bioterm-<name>:v1
#
# For multi-arch + push (requires GHCR_ORG in env):
#   GHCR_ORG=my-org scripts/build_images.sh --push
set -euo pipefail

MODE="--load"
ONLY="all"
TAG_PREFIX="${TAG_PREFIX:-bioterm}"
TAG_SUFFIX="${TAG_SUFFIX:-v1}"
PLATFORMS="${PLATFORMS:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --load) MODE="--load"; shift ;;
        --push) MODE="--push"; shift ;;
        --only) ONLY="$2"; shift 2 ;;
        --tag)  TAG_SUFFIX="$2"; shift 2 ;;
        --platforms) PLATFORMS="$2"; shift 2 ;;
        -h|--help)
            sed -n '1,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

if [[ -z "${PLATFORMS}" ]]; then
    if [[ "${MODE}" == "--push" ]]; then
        PLATFORMS="linux/amd64,linux/arm64"
    else
        # buildx --load only supports a single platform
        HOST_ARCH="$(uname -m)"
        case "${HOST_ARCH}" in
            x86_64|amd64) PLATFORMS="linux/amd64" ;;
            arm64|aarch64) PLATFORMS="linux/arm64" ;;
            *) echo "unsupported host arch: ${HOST_ARCH}" >&2; exit 2 ;;
        esac
    fi
fi

if [[ "${MODE}" == "--push" && -z "${GHCR_ORG:-}" ]]; then
    echo "GHCR_ORG must be set when using --push" >&2
    exit 2
fi

tag_for() {
    local name="$1"
    if [[ "${MODE}" == "--push" ]]; then
        echo "ghcr.io/${GHCR_ORG}/${TAG_PREFIX}-${name}:${TAG_SUFFIX}"
    else
        echo "${TAG_PREFIX}-${name}:${TAG_SUFFIX}"
    fi
}

ensure_builder() {
    if ! docker buildx inspect bioterm-builder >/dev/null 2>&1; then
        docker buildx create --name bioterm-builder --use >/dev/null
    else
        docker buildx use bioterm-builder >/dev/null
    fi
}

build_one() {
    local name="$1"
    local context="$2"
    local tag
    tag="$(tag_for "${name}")"
    echo ">>> Building ${tag} for ${PLATFORMS} (${MODE})"

    local extra_args=()
    if [[ "${name}" != "base" ]]; then
        # Derived images should point at the base tag we just built (or
        # have locally). Pass it via BASE_IMAGE build-arg.
        extra_args+=(--build-arg "BASE_IMAGE=$(tag_for base)")
    fi

    docker buildx build \
        --platform "${PLATFORMS}" \
        "${MODE}" \
        -t "${tag}" \
        ${extra_args[@]+"${extra_args[@]}"} \
        "${context}"
}

ensure_builder

case "${ONLY}" in
    base)    build_one base   docker/bioterm-base    ;;
    rnaseq)  build_one rnaseq docker/bioterm-rnaseq  ;;
    variant) build_one variant docker/bioterm-variant ;;
    all)
        build_one base    docker/bioterm-base
        build_one rnaseq  docker/bioterm-rnaseq
        build_one variant docker/bioterm-variant
        ;;
    *) echo "--only must be one of: base, rnaseq, variant, all" >&2; exit 2 ;;
esac
