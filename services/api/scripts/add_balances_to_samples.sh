#!/usr/bin/env bash
# add_balance_inplace_plainawk.sh
# Usage: ./add_balance_inplace_plainawk.sh /path/to/folder
# Adds a balance column to every .csv in the folder (in place).
# Works as long as CSVs are simple (no quoted commas).

set -euo pipefail

folder="${1:-}"
if [[ -z "$folder" || ! -d "$folder" ]]; then
  echo "Usage: $0 /path/to/folder" >&2
  exit 1
fi

for file in "$folder"/*.csv; do
  [[ -e "$file" ]] || continue
  echo "Updating $file ..."
  tmpfile="$(mktemp)"

  awk -F, -v OFS=',' '
    BEGIN { srand() }
    NR==1 {
      # map column headers to indexes
      for (i=1; i<=NF; i++) {
        col = tolower($i)
        gsub(/^[ \t]+|[ \t]+$/, "", col)
        if (col == "account_id") acc_i = i
        if (col == "amount") amt_i = i
      }
      if (!acc_i || !amt_i) {
        print "ERROR: Missing header in " FILENAME > "/dev/stderr"
        exit 2
      }
      print $0,"balance"
      next
    }
    {
      acc = $acc_i
      key = acc

      amt = $amt_i + 0
      if (!(key in bal)) {
        bal[key] = int(1000 + rand()*4000)
      }
      bal[key] += amt
      print $0, bal[key]
    }
  ' "$file" > "$tmpfile" && mv "$tmpfile" "$file"
done

echo "Done."
