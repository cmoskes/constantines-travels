#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
umask 077
runtime="${CONSTANTINES_IMPORTER_RUNTIME:-$HOME/Library/Application Support/Constantines Travels Importer/python-3.13}"
python="${CONSTANTINES_IMPORTER_PYTHON:-python3.13}"
is_compatible() {
  "$1" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 13) or sys.version_info.releaselevel != "final")'
}
if ! is_compatible "$python"; then
  printf '%s\n' 'Install a stable Python 3.13 release from python.org, then reopen Open Photo Importer.'
  exit 1
fi
if [ -e "$runtime" ] && ! is_compatible "$runtime/bin/python"; then
  mv "$runtime" "$runtime-old-$(date +%s)-$$"
fi
if [ ! -x "$runtime/bin/python" ]; then
  "$python" -m venv "$runtime"
fi
if ! cmp -s requirements.txt "$runtime/installed-requirements.txt" ||
   ! "$runtime/bin/python" -c 'import PIL, pillow_heif' >/dev/null 2>&1; then
  "$runtime/bin/python" -m pip --isolated install --index-url https://pypi.org/simple --only-binary=:all: --require-hashes -r requirements.txt
  cp requirements.txt "$runtime/installed-requirements.txt"
fi
exec "$runtime/bin/python" -B app.py --open "$@"
