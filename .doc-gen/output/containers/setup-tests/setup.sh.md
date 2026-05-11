# setup.sh

**Path:** containers/setup-tests/setup.sh
**Syntax:** bash
**Generated:** 2026-05-11 15:11:09

```bash
#!/usr/bin/env bash
# =============================================================================
# dev-utils container setup
# =============================================================================
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/carolynboyle/dev-utils/main/containers/setup-tests/setup.sh | bash -s <container-name>
#
# Example:
#   curl -fsSL https://raw.githubusercontent.com/carolynboyle/dev-utils/main/containers/setup-tests/setup.sh | bash -s python-test
#   curl -fsSL https://raw.githubusercontent.com/carolynboyle/dev-utils/main/containers/setup-tests/setup.sh | bash -s dev-utils-test
#
# What this script does:
#   1. Checks for required tools (docker, python3)
#   2. Fetches containers.yaml from the repo
#   3. Validates the requested container name
#   4. Creates ~/containers/<name>/ if it does not exist
#   5. Prompts for .env values, showing auto-detected defaults
#   6. Writes .env
#   7. Fetches container files from the repo
#   8. For containers with a base_image dependency, checks whether that
#      image exists and offers to build it first if not
#   9. Offers to run docker compose up --build
#
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
REPO_BASE="https://raw.githubusercontent.com/carolynboyle/dev-utils/main/containers"
REPO_RAW="${REPO_BASE}"
REGISTRY_URL="${REPO_BASE}/setup-tests/containers.yaml"
CONTAINERS_BASE="${HOME}/containers"

# -----------------------------------------------------------------------------
# Colours — degrade gracefully if terminal does not support them
# -----------------------------------------------------------------------------
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    RED='' GREEN='' YELLOW='' CYAN='' BOLD='' RESET=''
fi

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
info()    { echo -e "${CYAN}-->${RESET} $*"; }
success() { echo -e "${GREEN}✓${RESET} $*"; }
warn()    { echo -e "${YELLOW}warning:${RESET} $*"; }
error()   { echo -e "${RED}error:${RESET} $*" >&2; }
die()     { error "$*"; exit 1; }

prompt_with_default() {
    # Usage: prompt_with_default "Label" "default_value"
    # Prints prompt, reads input, returns default if input is empty
    local label="$1"
    local default="$2"
    local value

    if [ -n "${default}" ]; then
        printf "%s [%s]: " "${label}" "${default}"
    else
        printf "%s: " "${label}"
    fi

    read -r value
    echo "${value:-${default}}"
}

confirm() {
    # Usage: confirm "Question" — returns 0 for yes, 1 for no
    local question="$1"
    local answer
    printf "%s [Y/n]: " "${question}"
    read -r answer
    case "${answer}" in
        [nN]*) return 1 ;;
        *)     return 0 ;;
    esac
}

# -----------------------------------------------------------------------------
# Dependency checks
# -----------------------------------------------------------------------------
check_dependencies() {
    info "Checking required tools..."

    local missing=0

    if ! command -v docker &>/dev/null; then
        error "docker not found — install Docker before running this script"
        error "  https://docs.docker.com/engine/install/"
        missing=1
    fi

    if ! docker compose version &>/dev/null 2>&1; then
        error "docker compose not found — Docker Compose v2 is required"
        error "  https://docs.docker.com/compose/install/"
        missing=1
    fi

    if ! command -v python3 &>/dev/null; then
        error "python3 not found — required to read containers.yaml"
        missing=1
    else
        if ! python3 -c "import yaml" &>/dev/null 2>&1; then
            error "PyYAML not found — required to read containers.yaml"
            case "$(uname -s)" in
                Linux*)
                    error "  Install with: sudo apt install python3-yaml"
                    error "  (or the equivalent for your Linux distribution)"
                    ;;
                Darwin*)
                    error "  Install with: pip3 install pyyaml"
                    ;;
                *)
                    error "  Install with: pip3 install pyyaml"
                    ;;
            esac
            missing=1
        fi
    fi

    if ! command -v curl &>/dev/null; then
        error "curl not found — required to fetch files from GitHub"
        missing=1
    fi

    [ "${missing}" -eq 0 ] || die "Missing required tools — see above"
    success "All required tools found"
}

# -----------------------------------------------------------------------------
# Fetch and parse containers.yaml
# -----------------------------------------------------------------------------
fetch_registry() {
    info "Fetching container registry..."
    REGISTRY_FILE="$(mktemp /tmp/containers.yaml.XXXXXX)"
    curl -fsSL "${REGISTRY_URL}" -o "${REGISTRY_FILE}" \
        || die "Failed to fetch containers.yaml from ${REGISTRY_URL}"
    success "Registry loaded"
}

# Returns a value from the registry using python3 to parse yaml
# Usage: registry_get <container> <field>
registry_get() {
    local container="$1"
    local field="$2"
    python3 - <<EOF
import sys
try:
    import yaml
except ImportError:
    sys.exit("PyYAML not found — install it with: pip3 install pyyaml")

with open("${REGISTRY_FILE}", encoding="utf-8") as f:
    data = yaml.safe_load(f)

containers = data.get("containers", {})
if "${container}" not in containers:
    sys.exit("Unknown container: ${container}")

value = containers["${container}"].get("${field}")
if value is None:
    print("")
else:
    print(value)
EOF
}

# Returns a list of known container names
registry_list_containers() {
    python3 - <<EOF
import sys
try:
    import yaml
except ImportError:
    sys.exit("PyYAML not found — install it with: pip3 install pyyaml")

with open("${REGISTRY_FILE}", encoding="utf-8") as f:
    data = yaml.safe_load(f)

for name in data.get("containers", {}).keys():
    print(name)
EOF
}

# Returns env_vars as lines of: NAME|description|auto_detect_command
registry_get_env_vars() {
    local container="$1"
    python3 - <<EOF
import sys
try:
    import yaml
except ImportError:
    sys.exit("PyYAML not found — install it with: pip3 install pyyaml")

with open("${REGISTRY_FILE}", encoding="utf-8") as f:
    data = yaml.safe_load(f)

env_vars = data["containers"]["${container}"].get("env_vars", [])
for var in env_vars:
    name        = var.get("name", "")
    description = var.get("description", "").replace("|", " ")
    auto_detect = var.get("auto_detect") or ""
    print(f"{name}|{description}|{auto_detect}")
EOF
}

# Returns files as one per line
registry_get_files() {
    local container="$1"
    python3 - <<EOF
import sys
try:
    import yaml
except ImportError:
    sys.exit("PyYAML not found — install it with: pip3 install pyyaml")

with open("${REGISTRY_FILE}", encoding="utf-8") as f:
    data = yaml.safe_load(f)

for f in data["containers"]["${container}"].get("files", []):
    print(f)
EOF
}

# -----------------------------------------------------------------------------
# Validate container name
# -----------------------------------------------------------------------------
validate_container() {
    local requested="$1"
    local known

    known="$(registry_list_containers)"

    if ! echo "${known}" | grep -qx "${requested}"; then
        error "Unknown container: '${requested}'"
        echo ""
        echo "Available containers:"
        while IFS= read -r name; do
            local desc
            desc="$(registry_get "${name}" "description")"
            printf "  %-20s %s\n" "${name}" "${desc}"
        done <<< "${known}"
        echo ""
        die "Re-run with one of the container names listed above"
    fi
}

# -----------------------------------------------------------------------------
# Create working directory
# -----------------------------------------------------------------------------
create_workdir() {
    local container="$1"
    WORKDIR="${CONTAINERS_BASE}/${container}"

    if [ -d "${WORKDIR}" ]; then
        warn "Directory already exists: ${WORKDIR}"
    else
        mkdir -p "${WORKDIR}"
        success "Created ${WORKDIR}"
    fi
}

# -----------------------------------------------------------------------------
# Collect env vars and write .env
# -----------------------------------------------------------------------------
collect_env_vars() {
    local container="$1"
    local env_file="${WORKDIR}/.env"

    if [ -f "${env_file}" ]; then
        warn ".env already exists at ${env_file}"
        if ! confirm "Overwrite it?"; then
            info "Keeping existing .env"
            return
        fi
    fi

    echo ""
    echo -e "${BOLD}Configure .env for ${container}${RESET}"
    echo "Press Enter to accept the detected default, or type a new value."
    echo ""

    local env_contents=""

    while IFS='|' read -r name description auto_detect_cmd; do
        # Auto-detect default if a command is provided
        local default=""
        if [ -n "${auto_detect_cmd}" ]; then
            default="$(eval "${auto_detect_cmd}" 2>/dev/null || true)"
        fi

        echo -e "  ${CYAN}${name}${RESET}"
        echo "  ${description}"
        local value
        value="$(prompt_with_default "  Value" "${default}")"

        # Require a value if no default is available
        while [ -z "${value}" ]; do
            warn "A value is required for ${name}"
            value="$(prompt_with_default "  Value" "${default}")"
        done

        env_contents="${env_contents}${name}=${value}\n"
        echo ""

    done < <(registry_get_env_vars "${container}")

    printf "%s" "$(echo -e "${env_contents}")" > "${env_file}"
    success ".env written to ${env_file}"
}

# -----------------------------------------------------------------------------
# Fetch container files from repo
# -----------------------------------------------------------------------------
fetch_files() {
    local container="$1"

    info "Fetching container files from GitHub..."

    while IFS= read -r filename; do
        local dest="${WORKDIR}/${filename}"
        local url="${REPO_RAW}/${container}/${filename}"

        if [ -f "${dest}" ]; then
            warn "${filename} already exists"
            if ! confirm "Overwrite ${filename}?"; then
                info "Skipping ${filename}"
                continue
            fi
        fi

        curl -fsSL "${url}" -o "${dest}" \
            || die "Failed to fetch ${url}"
        success "Fetched ${filename}"

    done < <(registry_get_files "${container}")
}

# -----------------------------------------------------------------------------
# Handle base image dependency
# -----------------------------------------------------------------------------
handle_base_image() {
    local container="$1"
    local base_image
    base_image="$(registry_get "${container}" "base_image")"

    [ -z "${base_image}" ] && return

    info "Checking for base image: ${base_image}..."

    if docker images "${base_image}" -q | grep -q .; then
        success "Base image '${base_image}' found"
        return
    fi

    warn "Base image '${base_image}' not found locally"
    echo "  ${container} requires '${base_image}' to be built first."
    echo ""

    if confirm "Build '${base_image}' now?"; then
        local base_workdir="${CONTAINERS_BASE}/${base_image}"

        if [ ! -d "${base_workdir}" ]; then
            info "Setting up '${base_image}' first..."
            setup_container "${base_image}"
        else
            info "Building '${base_image}' from ${base_workdir}..."
            (cd "${base_workdir}" && docker compose up --build -d) \
                || die "Failed to build base image '${base_image}'"
            success "Base image '${base_image}' built"
        fi
    else
        die "Cannot continue without base image '${base_image}' — build it first"
    fi
}

# -----------------------------------------------------------------------------
# Offer to build
# -----------------------------------------------------------------------------
prompt_build() {
    local container="$1"
    echo ""
    if confirm "Build and start '${container}' now?"; then
        info "Running docker compose up --build..."
        (cd "${WORKDIR}" && docker compose up --build -d) \
            || die "docker compose up --build failed"
        success "Container '${container}' is running"
        echo ""
        echo "Useful commands:"
        echo "  docker compose exec ${container} bash   # open a shell"
        echo "  docker compose down                      # stop and remove"
        echo "  docker compose logs -f                   # follow logs"
    else
        echo ""
        info "Skipping build. When ready:"
        echo "  cd ${WORKDIR}"
        echo "  docker compose up --build"
    fi
}

# -----------------------------------------------------------------------------
# Full setup flow for one container
# -----------------------------------------------------------------------------
setup_container() {
    local container="$1"

    echo ""
    echo -e "${BOLD}=== Setting up: ${container} ===${RESET}"
    echo ""

    local desc
    desc="$(registry_get "${container}" "description")"
    echo "  ${desc}"
    echo ""

    create_workdir "${container}"
    collect_env_vars "${container}"
    fetch_files "${container}"
    handle_base_image "${container}"
    prompt_build "${container}"
}

# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
main() {
    echo ""
    echo -e "${BOLD}dev-utils container setup${RESET}"
    echo "=================================="

    [ "${#}" -ge 1 ] || die "Usage: ... | bash -s <container-name>"

    local container="$1"

    check_dependencies
    fetch_registry
    validate_container "${container}"
    setup_container "${container}"

    echo ""
    success "Done. See ${WORKDIR}/README.md for next steps."
    echo ""

    # Clean up temp file
    rm -f "${REGISTRY_FILE}"
}

main "$@"

```
