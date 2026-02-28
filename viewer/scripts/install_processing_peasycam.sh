#!/usr/bin/env bash
# Purpose: Install the PeasyCam Processing dependency in local/CI environments.
# Inputs: Command arguments and local runtime/tooling prerequisites.
# Outputs: Exit status and generated artifacts/logs for the invoked workflow.
# Usage: ./viewer/scripts/install_processing_peasycam.sh

set -euo pipefail

readonly PEASYCAM_URL="https://mrfeinberg.com/peasycam/peasycam.zip"
readonly PEASYCAM_SHA256="f4a89fd2be07cabcaee51eb72db4548a9dac8b79ae7bd1c79ae8a8132dcb66ff"

sha256() {
  local file="$1"

  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | awk '{print $1}'
    return 0
  fi

  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file" | awk '{print $1}'
    return 0
  fi

  if command -v openssl >/dev/null 2>&1; then
    openssl dgst -sha256 "$file" | awk '{print $2}'
    return 0
  fi

  echo "Required tool not found: sha256sum (or shasum/openssl)" >&2
  exit 1
}

resolve_sketchbook_path() {
  if [[ -n "${QAVE_PROCESSING_SKETCHBOOK:-}" ]]; then
    printf '%s\n' "$QAVE_PROCESSING_SKETCHBOOK"
    return
  fi

  local pref_candidates=(
    "$HOME/.config/processing/preferences.txt"
    "$HOME/.processing/preferences.txt"
    "$HOME/.var/app/org.processing.processing/config/processing/preferences.txt"
    "$HOME/Library/Processing/preferences.txt"
    "$HOME/Library/Application Support/processing/preferences.txt"
  )

  if [[ -n "${APPDATA:-}" ]]; then
    local appdata_posix="${APPDATA//\\//}"
    pref_candidates+=("$appdata_posix/Processing/preferences.txt")
  fi

  local pref_file=""
  local candidate=""
  for candidate in "${pref_candidates[@]}"; do
    if [[ -f "$candidate" ]]; then
      pref_file="$candidate"
      break
    fi
  done

  if [[ -n "$pref_file" ]]; then
    local configured
    configured="$(grep -E '^sketchbook\.path=' "$pref_file" | tail -n 1 | cut -d'=' -f2- || true)"
    configured="${configured//\\//}"
    if [[ -n "$configured" ]]; then
      printf '%s\n' "$configured"
      return
    fi
  fi

  local uname_s
  uname_s="$(uname -s)"
  local defaults=()
  case "$uname_s" in
    Darwin|MINGW*|MSYS*|CYGWIN*)
      defaults=("$HOME/Documents/Processing" "$HOME/sketchbook")
      ;;
    *)
      defaults=("$HOME/sketchbook" "$HOME/Documents/Processing")
      ;;
  esac

  for candidate in "${defaults[@]}"; do
    if [[ -d "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return
    fi
  done

  printf '%s\n' "${defaults[0]}"
}

validate_install() {
  local dir="$1"
  [[ -f "$dir/library.properties" ]] &&
    [[ -f "$dir/library/peasycam.jar" ]] &&
    [[ -f "$dir/library/peasy-math.jar" ]]
}

require_command() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found: $tool" >&2
    exit 1
  fi
}

main() {
  require_command curl
  require_command unzip

  local sketchbook
  sketchbook="$(resolve_sketchbook_path)"
  local libraries_dir="$sketchbook/libraries"
  local install_dir="$libraries_dir/peasycam"

  mkdir -p "$libraries_dir"

  if validate_install "$install_dir"; then
    echo "PeasyCam already installed: $install_dir"
    exit 0
  fi

  local tmpdir
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "${tmpdir:-}"' EXIT

  local archive="$tmpdir/peasycam.zip"
  local unpack_dir="$tmpdir/unpack"

  echo "Downloading PeasyCam from $PEASYCAM_URL"
  curl -fsSL "$PEASYCAM_URL" -o "$archive"

  local actual_sha
  actual_sha="$(sha256 "$archive")"
  if [[ "$actual_sha" != "$PEASYCAM_SHA256" ]]; then
    echo "PeasyCam checksum mismatch." >&2
    echo "Expected: $PEASYCAM_SHA256" >&2
    echo "Actual:   $actual_sha" >&2
    exit 1
  fi

  mkdir -p "$unpack_dir"
  unzip -q "$archive" -d "$unpack_dir"

  local extracted="$unpack_dir/peasycam"
  if [[ ! -d "$extracted" ]]; then
    echo "PeasyCam archive format unexpected. Missing top-level 'peasycam/' directory." >&2
    exit 1
  fi

  if ! validate_install "$extracted"; then
    echo "PeasyCam archive missing required files (library.properties / jars)." >&2
    exit 1
  fi

  local staged="$libraries_dir/.peasycam.$$"
  rm -rf "$staged"
  cp -R "$extracted" "$staged"
  rm -rf "$install_dir"
  mv "$staged" "$install_dir"

  if ! validate_install "$install_dir"; then
    echo "PeasyCam installation verification failed at $install_dir" >&2
    exit 1
  fi

  echo "PeasyCam installed: $install_dir"
}

main "$@"
