#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  musmem-social/open_tabs.sh LETTER GENDER PLATFORM [--dry-run]

Platforms: instagram, facebook, twitter

Examples:
  musmem-social/open_tabs.sh a male instagram
  musmem-social/open_tabs.sh b female instagram --dry-run
EOF
}

if [[ $# -lt 3 || $# -gt 4 ]]; then
  usage >&2
  exit 2
fi

letter=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
gender=$(printf '%s' "$2" | tr '[:upper:]' '[:lower:]')
platform=$(printf '%s' "$3" | tr '[:upper:]' '[:lower:]')
dry_run=0

if [[ $# -eq 4 ]]; then
  case "$4" in
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

if [[ "$gender" != "male" && "$gender" != "female" ]]; then
  echo "Expected gender: male or female, got: $2" >&2
  exit 2
fi

config_dir="$HOME/workspace/skills/musmemSkills/config"
social_media=$(python3 -c "import json,os; p=json.load(open('$config_dir/paths.json')); print(os.path.expanduser(p['social_media']))")

json_file="${social_media}/prelim-${letter}-${gender}.json"

if [[ ! -f "$json_file" ]]; then
  echo "No prelim file found: $json_file" >&2
  exit 1
fi

case "$platform" in
  instagram) jq_filter='.[].ig // empty | select(. != "") | "https://www.instagram.com/\(.)/"' ;;
  facebook)  jq_filter='.[].fb // empty | select(. != "") | "https://www.facebook.com/\(.)/"' ;;
  twitter)   jq_filter='.[].tw // empty | select(. != "") | "https://x.com/\(.)"' ;;
  *)
    echo "Expected platform: instagram, facebook, or twitter, got: $3" >&2
    exit 2
    ;;
esac

urls=()
while IFS= read -r url; do
  urls+=("$url")
done < <(jq -r "$jq_filter" "$json_file")

if [[ ${#urls[@]} -eq 0 ]]; then
  echo "No ${platform} handles found in $json_file" >&2
  exit 1
fi

printf 'Opening %d %s profiles from %s\n' "${#urls[@]}" "$platform" "$json_file"

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
