#!/usr/bin/env bash
# Purpose: Launch the Processing sketch with deterministic runtime flags.
# Inputs: Command arguments and local runtime/tooling prerequisites.
# Outputs: Exit status and generated artifacts/logs for the invoked workflow.
# Usage: ./viewer/scripts/run_processing.sh --trace <trace.json> [options]

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
sketch_dir="$repo_root/viewer/processing_qave"
peasycam_bootstrap="$repo_root/viewer/scripts/install_processing_peasycam.sh"
jvm_error_dir="${QAVE_JVM_ERROR_DIR:-$repo_root/artifacts/jvm_crash}"
force_native_launcher="${QAVE_PROCESSING_FORCE_NATIVE_LAUNCHER:-0}"
processing_cli_java_cmd=()

runner=""
runner_mode=""

if command -v Processing >/dev/null 2>&1; then
  runner="$(command -v Processing)"
  runner_mode="cli"
elif command -v processing-java >/dev/null 2>&1; then
  runner="$(command -v processing-java)"
  runner_mode="legacy"
fi

if [[ -z "$runner" ]]; then
  echo "Processing CLI is required on PATH." >&2
  echo "Install Processing 4.x and expose either 'processing-java' (legacy) or 'Processing' (new CLI)." >&2
  exit 1
fi

if [[ ! -d "$sketch_dir" ]]; then
  echo "Sketch directory not found: $sketch_dir" >&2
  exit 1
fi

if [[ ! -f "$peasycam_bootstrap" ]]; then
  echo "PeasyCam bootstrap script not found: $peasycam_bootstrap" >&2
  exit 1
fi

resolve_processing_root_from_runner() {
  local runner_path="$1"
  if [[ -z "$runner_path" ]]; then
    return 1
  fi

  local runner_realpath
  runner_realpath="$(readlink -f "$runner_path" 2>/dev/null || true)"
  if [[ -z "$runner_realpath" ]]; then
    return 1
  fi

  local runner_dir
  runner_dir="$(dirname "$runner_realpath")"
  local runner_name
  runner_name="$(basename "$runner_realpath")"
  if [[ "$runner_name" == "Processing" && "$(basename "$runner_dir")" == "bin" ]]; then
    dirname "$runner_dir"
    return 0
  fi

  return 1
}

build_processing_cli_java_command() {
  local processing_root="$1"
  local cfg_path="$processing_root/lib/app/Processing.cfg"
  local app_dir="$processing_root/lib/app"
  local java_bin="$app_dir/resources/jdk/bin/java"

  if [[ ! -f "$cfg_path" || ! -x "$java_bin" ]]; then
    return 1
  fi

  local payload
  payload="$(
    python3 - "$cfg_path" "$app_dir" <<'PY'
import sys
from pathlib import Path

cfg_path = Path(sys.argv[1])
app_dir = Path(sys.argv[2])
section = None
main_class = ""
classpath = []
java_opts = []

for raw in cfg_path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    if line.startswith("[") and line.endswith("]"):
        section = line[1:-1]
        continue
    if "=" not in line:
        continue
    key, value = line.split("=", 1)
    value = value.replace("$APPDIR", str(app_dir))
    if section == "Application":
        if key == "app.mainclass":
            main_class = value
        elif key == "app.classpath":
            classpath.append(value)
    elif section == "JavaOptions" and key == "java-options":
        java_opts.append(value)

if not main_class or not classpath:
    sys.exit(1)

print(main_class)
print(":".join(classpath))
for opt in java_opts:
    print(opt)
PY
  )" || return 1

  local main_class=""
  local classpath=""
  local java_opts=()
  local line_index=0
  while IFS= read -r line; do
    if [[ "$line_index" -eq 0 ]]; then
      main_class="$line"
    elif [[ "$line_index" -eq 1 ]]; then
      classpath="$line"
    elif [[ -n "$line" ]]; then
      java_opts+=("$line")
    fi
    line_index=$((line_index + 1))
  done <<<"$payload"

  if [[ -z "$main_class" || -z "$classpath" ]]; then
    return 1
  fi

  processing_cli_java_cmd=("$java_bin")
  processing_cli_java_cmd+=("${java_opts[@]}")
  processing_cli_java_cmd+=("-cp" "$classpath" "$main_class" "cli" "--sketch=$sketch_dir" "--run")
  if [[ $# -gt 1 ]]; then
    processing_cli_java_cmd+=("--")
    local arg
    for arg in "${@:2}"; do
      processing_cli_java_cmd+=("$arg")
    done
  fi

  return 0
}

# Resolve requested record mode from args so frame directory cleanup happens
# before Processing bootstraps recording.
record_mode=""
expect_record_value=0
for arg in "$@"; do
  if [[ "$expect_record_value" -eq 1 ]]; then
    record_mode="$arg"
    expect_record_value=0
    continue
  fi
  case "$arg" in
    --record)
      expect_record_value=1
      ;;
    --record=*)
      record_mode="${arg#--record=}"
      ;;
  esac
done
if [[ "$expect_record_value" -eq 1 ]]; then
  echo "Missing value for --record." >&2
  exit 1
fi
record_mode="${record_mode,,}"
if [[ "$record_mode" == "loop" || "$record_mode" == "full" ]]; then
  frames_dir="$sketch_dir/exports/frames"
  mkdir -p "$sketch_dir/exports"
  rm -rf "$frames_dir"
  mkdir -p "$frames_dir"
fi

bash "$peasycam_bootstrap"

mkdir -p "$jvm_error_dir"
jvm_error_file_flag="-XX:ErrorFile=$jvm_error_dir/hs_err_pid%p.log"
jvm_heap_dump_flag="-XX:HeapDumpPath=$jvm_error_dir"
if [[ -n "${JAVA_TOOL_OPTIONS:-}" ]]; then
  export JAVA_TOOL_OPTIONS="$jvm_error_file_flag $jvm_heap_dump_flag $JAVA_TOOL_OPTIONS"
else
  export JAVA_TOOL_OPTIONS="$jvm_error_file_flag $jvm_heap_dump_flag"
fi

if [[ $# -gt 0 ]]; then
  export QAVE_ARGS="$*"
else
  export QAVE_ARGS=""
fi

if [[ "$runner_mode" == "legacy" ]]; then
  "$runner" --sketch="$sketch_dir" --run -- "$@"
else
  if [[ "$force_native_launcher" != "1" && "$force_native_launcher" != "true" ]]; then
    processing_root=""
    processing_root="$(resolve_processing_root_from_runner "$runner" || true)"
    if [[ -n "$processing_root" ]]; then
      if build_processing_cli_java_command "$processing_root" "$@"; then
        if [[ "${#processing_cli_java_cmd[@]}" -gt 0 ]]; then
          "${processing_cli_java_cmd[@]}"
          exit $?
        fi
      fi
    fi
  fi
  "$runner" cli --sketch="$sketch_dir" --run "$@"
fi
