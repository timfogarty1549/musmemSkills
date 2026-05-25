#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  working-scripts/open_instagram_section_tabs.sh LETTER [--dry-run]

Examples:
  working-scripts/open_instagram_section_tabs.sh a
  working-scripts/open_instagram_section_tabs.sh A --dry-run
EOF
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage >&2
  exit 2
fi

letter=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
dry_run=0

if [[ $# -eq 2 ]]; then
  case "$2" in
    --dry-run) dry_run=1 ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
fi

if [[ ! "$letter" =~ ^[a-z]$ ]]; then
  echo "Expected a single letter A-Z, got: $1" >&2
  exit 2
fi

json_file="/Users/timfogarty/workspace/musmem/data/social-media/covid-male-${letter}-section-male.json"

if [[ ! -f "$json_file" ]]; then
  echo "No section file found: $json_file" >&2
  exit 1
fi

urls=()
while IFS= read -r url; do
  urls+=("$url")
done < <(
  jq -r '.[].ig // empty | select(. != "") | "https://www.instagram.com/\(.)/"' "$json_file"
)

if [[ ${#urls[@]} -eq 0 ]]; then
  echo "No Instagram handles found in $json_file" >&2
  exit 1
fi

printf 'Opening %d Instagram profiles from %s\n' "${#urls[@]}" "$json_file"

if [[ "$dry_run" -eq 1 ]]; then
  printf '%s\n' "${urls[@]}"
  exit 0
fi

count=0
for url in "${urls[@]}"; do
  open -a "Google Chrome" "$url"
  count=$((count + 1))
  if [[ $count -lt ${#urls[@]} && $((count % 50)) -eq 0 ]]; then
    read -n 1 -s -r -p "Opened $count profiles. Press any key to continue..."
    printf '\n'
  fi
  sleep 1
done
