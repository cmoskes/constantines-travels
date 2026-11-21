#!/bin/bash
set -eu
repo="$(cd "$(dirname "$0")/../.." && pwd -P)"
exec /bin/bash "$repo/Open Photo Importer.app/Contents/MacOS/open-importer" --development "$@"
