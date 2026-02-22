#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOS
Usage: $0 [single|historical]

Commands:
  single      Run a single basho (example: 202501)
  historical  Loop over all honbasho from 2000 to 2024

Examples:
  $0 single
  $0 historical
EOS
  exit 1
}

if [[ $# -lt 1 ]]; then
  usage
fi

COMMAND="$1"

case "$COMMAND" in
  single)
    echo "=== Single basho example: 202501 ==="
    uv run python -m sumodata --basho 202501 --raw-cache on
    ;;

  historical)
    MONTHS=(01 03 05 07 09 11)
    for year in $(seq 2000 2024); do
      for month in "${MONTHS[@]}"; do
        basho="${year}${month}"
        echo "=== Fetching basho ${basho} ==="
        uv run python -m sumodata --basho "${basho}" --raw-cache on
      done
    done
    ;;

  *)
    usage
    ;;
esac
