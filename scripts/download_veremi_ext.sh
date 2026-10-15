#!/bin/bash
# Resumable download + nested unzip of VeReMi Extension subsets from Zenodo (record 20090854, CC-BY 4.0).
# Usage: scripts/download_veremi_ext.sh ConstPos_1416 RandomPos_1416 ...   (names as in the Zenodo file list, without .zip)
# Each archive holds 2-3 nested one-hour zips (VeReMi_50400_54000_*, VeReMi_54000_57600_*, ...). Output: data/x_<Name>/...
# Zenodo is often slow (0.1-1 MB/s) and drops connections: curl resumes (-C -) and this loop retries. Nothing is deleted.
cd "$(dirname "$0")/.." && mkdir -p data && cd data || exit 1
for n in "$@"; do
  for i in $(seq 1 30); do
    curl -sSL -C - --retry 5 --retry-delay 3 -m 3000 -o "$n.zip" "https://zenodo.org/records/20090854/files/$n.zip?download=1" && break
    echo "retry $i $n"; sleep 3
  done
  unzip -tq "$n.zip" >/dev/null 2>&1 || { echo "FAIL $n (zip incomplete)"; continue; }
  mkdir -p "x_$n" && unzip -q -o "$n.zip" -d "x_$n" && for z in x_$n/*/VeReMi_*.zip; do d="${z%.zip}"; mkdir -p "$d" && unzip -q -o "$z" -d "$d"; done
  echo "ok $n"
done
