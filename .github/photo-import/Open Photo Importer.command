#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
runtime="${CONSTANTINES_IMPORTER_RUNTIME:-$HOME/Library/Application Support/Constantines Travels Importer/python}"
python="${CONSTANTINES_IMPORTER_PYTHON:-python3}"
if ! "$python" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
  printf '%s\n' 'Install Python 3.10 or newer from python.org, then open this launcher again.'
  exit 1
fi
if [ ! -x "$runtime/bin/python" ]; then
  "$python" -m venv "$runtime"
fi
if ! cmp -s requirements.txt "$runtime/installed-requirements.txt"; then
  "$runtime/bin/python" -m pip install -r requirements.txt
  cp requirements.txt "$runtime/installed-requirements.txt"
fi
exec "$runtime/bin/python" -B app.py --open "$@"
