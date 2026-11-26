#!/bin/sh
# Run from a source checkout with Python 3.9+ on PATH.
set -eu

root_dir=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
exoverse="$root_dir/plugins/exoverse/bin/exoverse-plugin"
evidence_dir=$(mktemp -d "${TMPDIR:-/tmp}/exoverse-alignment.XXXXXXXX")
expected_sha256=0defcc8ded373525ab26fe7dad88c237573f74ef766d17ed88367859d035511b

run_study() {
    "$exoverse" paired run --template monitor \
        --question 'Does the ledger reduce false completion alerts?' \
        --baseline activity --treatment ledger --prediction lower --out "$1"
}

printf 'Writing study and paper to %s\n' "$evidence_dir"
run_study "$evidence_dir/first-study"
"$exoverse" paired verify "$evidence_dir/first-study" --sha256 "$expected_sha256"

run_study "$evidence_dir/reproduced-study"
"$exoverse" paired verify "$evidence_dir/reproduced-study" --sha256 "$expected_sha256"
cmp "$evidence_dir/first-study/study.json" "$evidence_dir/reproduced-study/study.json"
cmp "$evidence_dir/first-study/paper.md" "$evidence_dir/reproduced-study/paper.md"

printf '\nVerified and reproduced both files. Read the paper at:\n%s\n' \
    "$evidence_dir/first-study/paper.md"
