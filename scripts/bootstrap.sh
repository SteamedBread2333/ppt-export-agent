#!/usr/bin/env bash
# One-shot install for a fresh clone: Python 3.11+ venv, package, LibreOffice, poppler.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -x /opt/homebrew/bin/brew ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [[ -x /usr/local/bin/brew ]]; then
  eval "$(/usr/local/bin/brew shellenv)"
fi

find_python() {
  local candidate
  for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
        command -v "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

PYTHON=""
if PYTHON="$(find_python)"; then
  :
elif [[ "$(uname -s)" == Darwin ]] && command -v brew >/dev/null 2>&1; then
  echo "Python 3.11+ not found; installing python@3.12 with Homebrew"
  HOMEBREW_NO_AUTO_UPDATE=1 brew install python@3.12
  eval "$(brew shellenv)"
  PYTHON="$(find_python)" || true
fi

if [[ -z "${PYTHON}" ]]; then
  echo "Python 3.11+ is required. Install it, then re-run ./scripts/bootstrap.sh" >&2
  exit 1
fi

echo "Using ${PYTHON} ($("${PYTHON}" -c 'import sys; print(sys.version.split()[0])'))"

"${PYTHON}" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"

ppt-expert setup
ppt-expert doctor

echo
echo "Install complete. Activate the environment with:"
echo "  source .venv/bin/activate"
echo "Then smoke-check with:"
echo "  ppt-expert demo --recipe use --delivery approve"
