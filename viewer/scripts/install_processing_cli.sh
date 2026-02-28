#!/usr/bin/env bash
# Purpose: Install the pinned Processing CLI for deterministic local/CI smoke runs.
# Inputs: Command arguments, local runtime/tooling prerequisites, and optional env overrides.
# Outputs: Installed Processing CLI under artifacts plus path/export hints.
# Usage: ./viewer/scripts/install_processing_cli.sh [--print-bin-dir|--print-export]

set -euo pipefail

readonly PROCESSING_VERSION="4.5.2"
readonly PROCESSING_TAG="processing-1313-4.5.2"
readonly PROCESSING_ARCHIVE="processing-4.5.2-linux-x64-portable.zip"
readonly PROCESSING_URL="https://github.com/processing/processing4/releases/download/${PROCESSING_TAG}/${PROCESSING_ARCHIVE}"
readonly PROCESSING_SHA256="5d5ce0f5a59cffc86f12b49997184434f554ff546932323f148aad92626bc3ff"

usage() {
  echo "Usage: $0 [--print-bin-dir|--print-export]"
}

require_command() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found: $tool" >&2
    exit 1
  fi
}

emit_install_path() {
  local bin_dir="$1"
  local mode="$2"

  case "$mode" in
    print-bin-dir)
      printf '%s\n' "$bin_dir"
      ;;
    print-export)
      printf 'export PATH="%s:$PATH"\n' "$bin_dir"
      ;;
    *)
      echo "Processing CLI ready: $bin_dir"
      echo "To use it in your current shell session, run:"
      echo "export PATH=\"$bin_dir:\$PATH\""
      ;;
  esac
}

resolve_install_bin_dir() {
  local install_dir="$1"
  if [[ -x "$install_dir/bin/Processing" ]] || [[ -x "$install_dir/bin/processing-java" ]]; then
    printf '%s\n' "$install_dir/bin"
    return 0
  fi

  if [[ -x "$install_dir/processing-java" ]] || [[ -x "$install_dir/Processing" ]]; then
    printf '%s\n' "$install_dir"
    return 0
  fi

  return 1
}

validate_install() {
  local install_dir="$1"
  resolve_install_bin_dir "$install_dir" >/dev/null
}

resolve_existing_processing_dir() {
  local candidate=""
  if command -v processing-java >/dev/null 2>&1; then
    candidate="$(dirname "$(command -v processing-java)")"
    printf '%s\n' "$candidate"
    return 0
  fi

  if command -v Processing >/dev/null 2>&1; then
    candidate="$(dirname "$(command -v Processing)")"
    printf '%s\n' "$candidate"
    return 0
  fi

  return 1
}

main() {
  local mode="default"
  if [[ $# -gt 1 ]]; then
    usage
    exit 1
  fi

  if [[ $# -eq 1 ]]; then
    case "$1" in
      --print-bin-dir)
        mode="print-bin-dir"
        ;;
      --print-export)
        mode="print-export"
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        usage
        exit 1
        ;;
    esac
  fi

  local repo_root
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  local install_root="${QAVE_PROCESSING_INSTALL_ROOT:-$repo_root/artifacts/tooling/processing}"
  local install_dir="$install_root/processing-${PROCESSING_VERSION}"
  local stamp_file="$install_dir/.qave_processing_sha256"

  local uname_s
  uname_s="$(uname -s)"
  local uname_m
  uname_m="$(uname -m)"

  if [[ "$uname_s" != "Linux" || "$uname_m" != "x86_64" ]]; then
    local existing_dir=""
    if existing_dir="$(resolve_existing_processing_dir)"; then
      emit_install_path "$existing_dir" "$mode"
      return 0
    fi

    echo "Auto-bootstrap currently supports Linux x86_64 only." >&2
    echo "Install Processing manually and expose 'processing-java' or 'Processing' on PATH." >&2
    return 1
  fi

  require_command curl
  require_command unzip
  require_command sha256sum

  if ! validate_install "$install_dir" || [[ ! -f "$stamp_file" ]] || [[ "$(cat "$stamp_file")" != "$PROCESSING_SHA256" ]]; then
    local tmpdir
    tmpdir="$(mktemp -d)"
    trap 'rm -rf "${tmpdir:-}"' EXIT

    local archive="$tmpdir/$PROCESSING_ARCHIVE"
    local unpack_root="$tmpdir/unpack"
    local extracted_dir="$unpack_root/Processing"

    echo "Downloading Processing ${PROCESSING_VERSION} from ${PROCESSING_URL}"
    curl -fsSL "$PROCESSING_URL" -o "$archive"

    local actual_sha
    actual_sha="$(sha256sum "$archive" | awk '{print $1}')"
    if [[ "$actual_sha" != "$PROCESSING_SHA256" ]]; then
      echo "Processing checksum mismatch." >&2
      echo "Expected: $PROCESSING_SHA256" >&2
      echo "Actual:   $actual_sha" >&2
      return 1
    fi

    mkdir -p "$unpack_root"
    unzip -q "$archive" -d "$unpack_root"
    if [[ ! -d "$extracted_dir" ]]; then
      echo "Unexpected Processing archive layout: missing $extracted_dir" >&2
      return 1
    fi

    mkdir -p "$install_root"
    local staged_dir="$install_root/.processing-${PROCESSING_VERSION}.$$"
    rm -rf "$staged_dir" "$install_dir"
    mv "$extracted_dir" "$staged_dir"
    mv "$staged_dir" "$install_dir"

    if [[ -f "$install_dir/bin/processing-java" ]]; then
      chmod +x "$install_dir/bin/processing-java"
    fi
    if [[ -f "$install_dir/bin/Processing" ]]; then
      chmod +x "$install_dir/bin/Processing"
    fi
    if [[ -f "$install_dir/processing-java" ]]; then
      chmod +x "$install_dir/processing-java"
    fi
    if [[ -f "$install_dir/Processing" ]]; then
      chmod +x "$install_dir/Processing"
    fi
    printf '%s\n' "$PROCESSING_SHA256" > "$stamp_file"
  fi

  if ! validate_install "$install_dir"; then
    echo "Processing installation verification failed at $install_dir" >&2
    return 1
  fi

  local install_bin_dir=""
  install_bin_dir="$(resolve_install_bin_dir "$install_dir")"

  if [[ ":$PATH:" != *":$install_bin_dir:"* ]]; then
    export PATH="$install_bin_dir:$PATH"
  fi

  emit_install_path "$install_bin_dir" "$mode"
}

main "$@"
