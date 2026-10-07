#!/usr/bin/env bash
set -euo pipefail

TARGET_EXEC_MODE="${TARGET_EXEC_MODE:-host}"
TARGET_EXEC_CONTAINER="${TARGET_EXEC_CONTAINER:-}"
DOCKER_HELPER_MANAGED_RUN_ROOT="${DOCKER_HELPER_MANAGED_RUN_ROOT:-/tmp/aivuda-managed-docker-exec}"
DOCKER_HELPER_ACTIVE_MANAGED_CONTAINER=""
DOCKER_HELPER_ACTIVE_MANAGED_RUN_DIR=""
DOCKER_HELPER_ACTIVE_MANAGED_LOCK_DIR=""
DOCKER_HELPER_ACTIVE_MANAGED_RUNNING=0

docker_helper_has_docker() {
  command -v docker >/dev/null 2>&1
}

docker_helper_list_running_containers() {
  if ! docker_helper_has_docker; then
    return 0
  fi

  docker ps --format '{{.Names}}'
}

docker_helper_is_container_running() {
  local container_name="$1"

  if ! docker_helper_has_docker; then
    return 1
  fi

  docker ps --format '{{.Names}}' | grep -Fx "${container_name}" >/dev/null 2>&1
}

docker_helper_container_exists() {
  local container_name="$1"

  if ! docker_helper_has_docker; then
    return 1
  fi

  docker ps -a --format '{{.Names}}' | grep -Fx "${container_name}" >/dev/null 2>&1
}

docker_helper_require_running_container() {
  local container_name="$1"
  local error_prefix="${2:-[docker_helper]}"

  if ! docker_helper_has_docker; then
    echo "${error_prefix} docker not found" >&2
    return 1
  fi

  if [[ -z "${container_name}" ]]; then
    echo "${error_prefix} docker container name is empty" >&2
    return 1
  fi

  if ! docker_helper_is_container_running "${container_name}"; then
    if ! docker_helper_container_exists "${container_name}"; then
      echo "${error_prefix} docker container does not exist: ${container_name}" >&2
      return 1
    fi

    echo "${error_prefix} docker container must already be running: ${container_name}" >&2
    return 1
  fi
}

docker_helper_require_python_yaml() {
  local config_path_for_error="${1:-YAML config}"

  if ! command -v python3 >/dev/null 2>&1; then
    echo -e "\033[91mpython3 is required to update ${config_path_for_error}.\033[0m" >&2
    return 1
  fi

  if ! python3 -c "import yaml" >/dev/null 2>&1; then
    echo -e "\033[91mPyYAML is required to update ${config_path_for_error}.\033[0m" >&2
    return 1
  fi
}

docker_helper_set_yaml_value() {
  local config_path="$1"
  local dotted_key="$2"
  local value_type="${3:-string}"
  local raw_value="${4:-}"

  docker_helper_require_python_yaml "${config_path}" || return 1

  python3 - "${config_path}" "${dotted_key}" "${value_type}" "${raw_value}" <<'PY'
import sys
from pathlib import Path
import yaml

config_path = Path(sys.argv[1])
dotted_key = sys.argv[2]
value_type = sys.argv[3]
raw_value = sys.argv[4]

cfg = {}
if config_path.is_file():
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

if not isinstance(cfg, dict):
    raise SystemExit(f"root YAML node must be an object: {config_path}")

if not dotted_key:
    raise SystemExit("dotted_key must not be empty")

parts = dotted_key.split(".")
cursor = cfg
for part in parts[:-1]:
    child = cursor.get(part)
    if not isinstance(child, dict):
        child = {}
        cursor[part] = child
    cursor = child

if value_type == "bool":
    value = raw_value.lower() == "true"
elif value_type == "string":
    value = raw_value
else:
    raise SystemExit(f"unsupported docker_helper_set_yaml_value type: {value_type}")

cursor[parts[-1]] = value

config_path.write_text(
    yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False),
    encoding="utf-8",
)
PY
}

docker_helper_exec_bash() {
  local container_name="$1"
  shift
  local command="$*"
  local python_unbuffered="${PYTHONUNBUFFERED:-1}"
  local rosconsole_stdout_line_buffered="${ROSCONSOLE_STDOUT_LINE_BUFFERED:-1}"
  local term_value="${TERM:-xterm-256color}"
  local clicolor_force="${CLICOLOR_FORCE:-1}"
  local force_color="${FORCE_COLOR:-1}"
  local py_colors="${PY_COLORS:-1}"
  local managed_id
  local lock_id
  local run_dir
  local lock_dir
  local quoted_command
  local previous_exit_trap
  local previous_int_trap
  local previous_term_trap
  local previous_hup_trap
  local exit_code

  if [[ "${DOCKER_HELPER_ACTIVE_MANAGED_RUNNING}" -eq 1 ]]; then
    echo "[docker_helper] managed docker exec is already running in this shell." >&2
    echo "[docker_helper] nested managed docker exec calls are not supported." >&2
    echo "[docker_helper] active container: ${DOCKER_HELPER_ACTIVE_MANAGED_CONTAINER}" >&2
    echo "[docker_helper] active run dir: ${DOCKER_HELPER_ACTIVE_MANAGED_RUN_DIR}" >&2
    return 1
  fi

  lock_id="${AIVUDA_APP_ID:-aivuda}-$$"
  lock_id="${lock_id//[^A-Za-z0-9_.-]/_}"
  lock_dir="${DOCKER_HELPER_MANAGED_RUN_ROOT}/host-locks/${lock_id}.lock"
  docker_helper_acquire_managed_exec_lock "${lock_dir}" || return 1

  managed_id="${AIVUDA_APP_ID:-aivuda}-$$-$(date +%s)-${BASHPID:-$$}"
  managed_id="${managed_id//[^A-Za-z0-9_.-]/_}"
  run_dir="${DOCKER_HELPER_MANAGED_RUN_ROOT}/${managed_id}"
  quoted_command="$(printf '%q' "${command}")"

  previous_exit_trap="$(trap -p EXIT || true)"
  previous_int_trap="$(trap -p INT || true)"
  previous_term_trap="$(trap -p TERM || true)"
  previous_hup_trap="$(trap -p HUP || true)"

  DOCKER_HELPER_ACTIVE_MANAGED_CONTAINER="${container_name}"
  DOCKER_HELPER_ACTIVE_MANAGED_RUN_DIR="${run_dir}"
  DOCKER_HELPER_ACTIVE_MANAGED_LOCK_DIR="${lock_dir}"
  DOCKER_HELPER_ACTIVE_MANAGED_RUNNING=1

  trap 'docker_helper_active_managed_cleanup; DOCKER_HELPER_ACTIVE_MANAGED_RUNNING=0; docker_helper_restore_trap INT "${previous_int_trap}"; kill -INT $$' INT
  trap 'docker_helper_active_managed_cleanup; DOCKER_HELPER_ACTIVE_MANAGED_RUNNING=0; docker_helper_restore_trap TERM "${previous_term_trap}"; kill -TERM $$' TERM
  trap 'docker_helper_active_managed_cleanup; DOCKER_HELPER_ACTIVE_MANAGED_RUNNING=0; docker_helper_restore_trap HUP "${previous_hup_trap}"; kill -HUP $$' HUP
  trap 'docker_helper_active_managed_cleanup' EXIT

  docker exec -i \
    -e "PYTHONUNBUFFERED=${python_unbuffered}" \
    -e "ROSCONSOLE_STDOUT_LINE_BUFFERED=${rosconsole_stdout_line_buffered}" \
    -e "TERM=${term_value}" \
    -e "CLICOLOR_FORCE=${clicolor_force}" \
    -e "FORCE_COLOR=${force_color}" \
    -e "PY_COLORS=${py_colors}" \
    "${container_name}" \
    bash -lc "
set -e
run_dir=$(printf '%q' "${run_dir}")
command=${quoted_command}
mkdir -p \"\${run_dir}\"
rm -f \"\${run_dir}/pid\" \"\${run_dir}/pgid\"

cleanup() {
  local child_pid=\"\${child_pid:-}\"
  if [[ -n \"\${child_pid}\" ]] && kill -0 \"\${child_pid}\" >/dev/null 2>&1; then
    if [[ -f \"\${run_dir}/pgid\" ]]; then
      kill -TERM -- -\"\${child_pid}\" >/dev/null 2>&1 || kill -TERM \"\${child_pid}\" >/dev/null 2>&1 || true
      sleep 2
      kill -KILL -- -\"\${child_pid}\" >/dev/null 2>&1 || kill -KILL \"\${child_pid}\" >/dev/null 2>&1 || true
    else
      kill -TERM \"\${child_pid}\" >/dev/null 2>&1 || true
      sleep 2
      kill -KILL \"\${child_pid}\" >/dev/null 2>&1 || true
    fi
  fi
  rm -rf \"\${run_dir}\" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM HUP

if command -v setsid >/dev/null 2>&1; then
  setsid bash -lc \"\${command}\" &
  child_pid=\$!
  : >\"\${run_dir}/pgid\"
else
  bash -lc \"\${command}\" &
  child_pid=\$!
fi
printf '%s\n' \"\${child_pid}\" >\"\${run_dir}/pid\"
wait \"\${child_pid}\"
" || exit_code=$?

  exit_code="${exit_code:-0}"
  DOCKER_HELPER_ACTIVE_MANAGED_RUNNING=0
  docker_helper_stop_managed_exec "${container_name}" "${run_dir}"
  docker_helper_release_managed_exec_lock "${lock_dir}"
  DOCKER_HELPER_ACTIVE_MANAGED_CONTAINER=""
  DOCKER_HELPER_ACTIVE_MANAGED_RUN_DIR=""
  DOCKER_HELPER_ACTIVE_MANAGED_LOCK_DIR=""

  docker_helper_restore_trap EXIT "${previous_exit_trap}"
  docker_helper_restore_trap INT "${previous_int_trap}"
  docker_helper_restore_trap TERM "${previous_term_trap}"
  docker_helper_restore_trap HUP "${previous_hup_trap}"

  return "${exit_code}"
}

docker_helper_stop_managed_exec() {
  local container_name="$1"
  local run_dir="$2"
  local quoted_run_dir

  if [[ -z "${container_name}" || -z "${run_dir}" ]]; then
    return 0
  fi

  if ! docker_helper_is_container_running "${container_name}"; then
    return 0
  fi

  quoted_run_dir="$(printf '%q' "${run_dir}")"
  docker exec "${container_name}" bash -lc "
run_dir=${quoted_run_dir}
pid_file=\"\${run_dir}/pid\"
pgid_file=\"\${run_dir}/pgid\"
if [[ -f \"\${pid_file}\" ]]; then
  pid=\"\$(cat \"\${pid_file}\" 2>/dev/null || true)\"
  if [[ -n \"\${pid}\" ]] && kill -0 \"\${pid}\" >/dev/null 2>&1; then
    if [[ -f \"\${pgid_file}\" ]]; then
      kill -TERM -- -\"\${pid}\" >/dev/null 2>&1 || kill -TERM \"\${pid}\" >/dev/null 2>&1 || true
      sleep 2
      kill -KILL -- -\"\${pid}\" >/dev/null 2>&1 || kill -KILL \"\${pid}\" >/dev/null 2>&1 || true
    else
      kill -TERM \"\${pid}\" >/dev/null 2>&1 || true
      sleep 2
      kill -KILL \"\${pid}\" >/dev/null 2>&1 || true
    fi
  fi
fi
rm -rf \"\${run_dir}\" >/dev/null 2>&1 || true
" >/dev/null 2>&1 || true
}

docker_helper_active_managed_cleanup() {
  if [[ "${DOCKER_HELPER_ACTIVE_MANAGED_RUNNING}" -eq 1 ]]; then
    docker_helper_stop_managed_exec "${DOCKER_HELPER_ACTIVE_MANAGED_CONTAINER}" "${DOCKER_HELPER_ACTIVE_MANAGED_RUN_DIR}"
    docker_helper_release_managed_exec_lock "${DOCKER_HELPER_ACTIVE_MANAGED_LOCK_DIR}"
  fi
}

docker_helper_acquire_managed_exec_lock() {
  local lock_dir="$1"
  local lock_root

  lock_root="$(dirname "${lock_dir}")"
  mkdir -p "${lock_root}"

  if ! mkdir "${lock_dir}" 2>/dev/null; then
    echo "[docker_helper] managed docker exec is already running in this start.sh process." >&2
    echo "[docker_helper] concurrent or nested managed docker exec calls are not supported." >&2
    echo "[docker_helper] lock: ${lock_dir}" >&2
    return 1
  fi
}

docker_helper_release_managed_exec_lock() {
  local lock_dir="$1"

  if [[ -n "${lock_dir}" ]]; then
    rm -rf "${lock_dir}" >/dev/null 2>&1 || true
  fi
}

docker_helper_restore_trap() {
  local signal="$1"
  local previous="$2"

  if [[ -n "${previous}" ]]; then
    eval "${previous}"
  else
    trap - "${signal}"
  fi
}

docker_helper_target_use_host() {
  TARGET_EXEC_MODE="host"
  TARGET_EXEC_CONTAINER=""
  echo "[docker_helper] set target to host"
}

docker_helper_target_use_docker_container() {
  local container_name="$1"

  if [[ -z "${container_name}" ]]; then
    echo "[docker_helper] docker container name is empty" >&2
    return 1
  fi

  TARGET_EXEC_MODE="docker"
  TARGET_EXEC_CONTAINER="${container_name}"
  echo "[docker_helper] set target to docker container: ${container_name}"
}

docker_helper_target_mode() {
  printf '%s' "${TARGET_EXEC_MODE}"
}

docker_helper_target_container() {
  printf '%s' "${TARGET_EXEC_CONTAINER}"
}

docker_helper_target_is_docker() {
  [[ "${TARGET_EXEC_MODE}" == "docker" ]]
}

docker_helper_target_has_container() {
  [[ -n "${TARGET_EXEC_CONTAINER}" ]]
}

docker_helper_target_describe() {
  if docker_helper_target_is_docker; then
    printf 'container %s' "${TARGET_EXEC_CONTAINER}"
  else
    printf 'host'
  fi
}

docker_helper_target_select_install_target() {
  local container_name
  local choice
  local index
  local running_containers=()

  if docker_helper_has_docker; then
    mapfile -t running_containers < <(docker_helper_list_running_containers)
  fi

  if [[ ! -t 0 ]]; then
    docker_helper_target_use_host
    echo "[docker_helper] selected target: host" >&2
    return 0
  fi

  echo "Select installation target:" >&2
  echo "  1) host" >&2
  for index in "${!running_containers[@]}"; do
    printf '  %d) %s (docker container)\n' "$((index + 2))" "${running_containers[index]}" >&2
  done

  while true; do
    read -r -p "Enter selection [1]: " choice
    if [[ -z "${choice}" ]]; then
      choice="1"
    fi

    if [[ "${choice}" == "1" ]]; then
      docker_helper_target_use_host
      echo "[docker_helper] selected target: host" >&2
      return 0
    fi

    if [[ "${choice}" =~ ^[0-9]+$ ]]; then
      index=$((choice - 2))
      if (( index >= 0 && index < ${#running_containers[@]} )); then
        container_name="${running_containers[index]}"
        docker_helper_target_use_docker_container "${container_name}"
        echo "[docker_helper] selected target: $(docker_helper_target_describe)" >&2
        return 0
      fi
    fi

    echo "Please enter a valid option number." >&2
  done
}

docker_helper_target_require_available() {
  local error_prefix="${1:-[target_exec]}"

  case "${TARGET_EXEC_MODE}" in
    host)
      return 0
      ;;
    docker)
      docker_helper_require_running_container "${TARGET_EXEC_CONTAINER}" "${error_prefix}"
      ;;
    *)
      echo "${error_prefix} unsupported target mode: ${TARGET_EXEC_MODE}" >&2
      return 1
      ;;
  esac
}

docker_helper_target_exec_bash() {
  local command="$1"

  case "${TARGET_EXEC_MODE}" in
    host)
      bash -lc "${command}"
      ;;
    docker)
      docker_helper_target_require_available "[target_exec]" || return 1
      docker_helper_exec_bash "${TARGET_EXEC_CONTAINER}" "${command}"
      ;;
    *)
      echo "[target_exec] unsupported target mode: ${TARGET_EXEC_MODE}" >&2
      return 1
      ;;
  esac
}
