#!/usr/bin/env bash
# Run pdf2md.py inside a cached virtualenv, creating it on first use.
# The venv lives outside the skills repo so nothing heavy gets committed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${PDF2MD_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/pdf-to-markdown/venv}"
# pymupdf4llm refuses to import unless pymupdf has the exact same version.
PINS=(pymupdf4llm==1.28.2 pymupdf==1.28.2 pymupdf-layout==1.28.2)
STAMP="${VENV}/.pins"

if ! command -v python3 >/dev/null 2>&1; then
  printf 'pdf2md: python3 is required\n' >&2
  exit 69
fi

if [[ ! -x "${VENV}/bin/python" ]] || [[ "$(cat "${STAMP}" 2>/dev/null)" != "${PINS[*]}" ]]; then
  printf 'pdf2md: setting up %s (first run only)\n' "${VENV}" >&2
  python3 -m venv "${VENV}"
  "${VENV}/bin/python" -m pip install --quiet --upgrade pip
  "${VENV}/bin/python" -m pip install --quiet "${PINS[@]}"
  printf '%s' "${PINS[*]}" > "${STAMP}"
fi

exec "${VENV}/bin/python" "${SCRIPT_DIR}/pdf2md.py" "$@"
