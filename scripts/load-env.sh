(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ $sourced -eq 0 ]; then
  echo "ERROR, this script is meant to be sourced."
  exit 1
fi

# Load Environment Script
# Decrypts .env.integration.enc and generates .env (Docker) and .env.shell (shell cache).

# figure out some paths
mydir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
repo_root="${mydir}/.."

# Use repo Docker CLI config (no credential helper) so DinD is independent of the host.
export DOCKER_CONFIG="${repo_root}/.docker"

# pre-commit and other dev tools live in the uv venv (not on PATH by default)
if [ -d "${repo_root}/.venv/bin" ]; then
    case ":${PATH}:" in
        *:"${repo_root}/.venv/bin":*) ;;
        *) export PATH="${repo_root}/.venv/bin:${PATH}" ;;
    esac
fi

# Setup aliases (completions: static files in image + bash-completion lazy-load)
alias k=kubectl
alias d=docker
alias kda="kubectl delete all,pdb,configmap,secret,pvc,ingress,serviceaccount,endpoints --all"
alias kga="kubectl get all,pdb,configmap,secret,pvc,ingress,serviceaccount,endpoints"
alias ksn="kubectl config set-context --current --namespace"

# Set bash completion for aliases
declare -F __start_kubectl &>/dev/null && complete -o default -F __start_kubectl k
declare -F __start_docker &>/dev/null && complete -o default -F __start_docker d

# ggshield (dev dependency in .venv; same PATH as pre-commit above)
if command -v ggshield &> /dev/null; then
    if [ -n "${GITGUARDIAN_API_KEY:-}" ]; then
        echo "✅ ggshield: using GITGUARDIAN_API_KEY from environment"
    elif [ -f ~/.config/ggshield/auth_config.yaml ] && grep -q "token:" ~/.config/ggshield/auth_config.yaml 2>/dev/null; then
        echo "✅ ggshield: authenticated (~/.config/ggshield/auth_config.yaml)"
    else
        echo "🔐 ggshield not authenticated — run: ggshield auth login --method token"
        echo "   Or set GITGUARDIAN_API_KEY (non-interactive)"
    fi
else
    echo "⚠️ ggshield not available - run: uv sync --dev --all-packages"
fi

ENCRYPTED_FILE="${mydir}/../.env.integration.enc"
DECRYPTED_FILE="${mydir}/../.env"
SHELL_ENV_FILE="${DECRYPTED_FILE}.shell"

_load_shell_env() {
    if [ -n "${GITLAB_API_TOKEN:-}" ]; then
        echo "✅ Environment variables already loaded"
        return 0
    fi

    if [ -f "$SHELL_ENV_FILE" ] && { [ ! -f "$ENCRYPTED_FILE" ] || [ ! "$ENCRYPTED_FILE" -nt "$SHELL_ENV_FILE" ]; }; then
        echo "🔄 Loading environment variables from $SHELL_ENV_FILE..."
        set -a
        # shellcheck source=/dev/null
        source "$SHELL_ENV_FILE"
        set +a
        echo "✅ Environment variables loaded from $SHELL_ENV_FILE"
        return 0
    fi

    if [ -f "$DECRYPTED_FILE" ] && [ -s "$DECRYPTED_FILE" ]; then
        echo "🔄 Loading environment variables from $DECRYPTED_FILE..."
        set -a
        # shellcheck source=/dev/null
        source "$DECRYPTED_FILE"
        set +a
        echo "✅ Environment variables loaded from $DECRYPTED_FILE"
        return 0
    fi

    return 1
}

# Check if SOPS is available
if ! command -v sops &> /dev/null; then
    echo "⚠️ SOPS not available - skipping secrets loading"
    _load_shell_env || true
    return 0
fi

# Check if encrypted file exists
if [ ! -f "$ENCRYPTED_FILE" ]; then
    echo "⚠️ $ENCRYPTED_FILE not found - skipping secrets loading"
    _load_shell_env || true
    return 0
fi

# Decrypt the encrypted file when cache is missing or stale
if grep -q '"sops"' "$ENCRYPTED_FILE" 2>/dev/null; then
    if [ ! -f "$DECRYPTED_FILE" ] || [ "$ENCRYPTED_FILE" -nt "$DECRYPTED_FILE" ]; then
        if decrypted_secrets=$(sops -d "$ENCRYPTED_FILE" 2>/dev/null); then
            # CLIENT_KEY breaks Docker's --env-file parser; omit it from the on-disk .env only.
            printf '%s\n' "$decrypted_secrets" | perl -0777 -pe 's/CLIENT_KEY=".*?"\n?//gs' > "$DECRYPTED_FILE"
            printf '%s\n' "$decrypted_secrets" > "$SHELL_ENV_FILE"
            chmod 600 "$DECRYPTED_FILE" "$SHELL_ENV_FILE"
            echo "✅ Encrypted secrets decrypted to $DECRYPTED_FILE (CLIENT_KEY omitted for Docker compatibility)"
        else
            echo "❌ Error decrypting $ENCRYPTED_FILE"
            echo "💡 Possible causes:"
            echo "   - Wrong GPG password"
            echo "   - GPG key not available"
            echo "   - SOPS configuration error"
            echo "📝 Tests may fail without valid GITLAB_API_TOKEN"
            _load_shell_env || true
            return 0  # Graceful return so sourcing continues
        fi
    fi

    _load_shell_env || true
else
    echo "⚠️ $ENCRYPTED_FILE is not encrypted or not in SOPS format"
    echo "📝 Tests may fail without valid GITLAB_API_TOKEN"
    _load_shell_env || true
    return 0  # Graceful return so sourcing continues
fi
