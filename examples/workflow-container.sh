#!/bin/sh
# Runs or verifies JSON workflow evidence without network access.
set -eu

usage() {
    printf '%s\n' 'Usage: sh examples/workflow-container.sh IMAGE_ID run workflow.json' \
        '       sh examples/workflow-container.sh IMAGE_ID verify evidence.json SHA256'
    exit 2
}

[ "$#" -ge 3 ] || usage
image_id=$1
mode=$2
file=$3
[ -f "$file" ] || usage
case "$image_id" in sha256:*) ;; *) usage ;; esac
hash=${image_id#sha256:}
case "$hash" in *[!a-f0-9]*) usage ;; esac
[ "${#hash}" -eq 64 ] || usage
root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
source_dir=$(CDPATH='' cd -- "$(dirname -- "$file")" && pwd)
source_file="$source_dir/$(basename -- "$file")"
case "$source_file,$root" in *'
'*) usage ;; esac
case "$source_file" in *,*|*\"*) usage ;; esac
case "$root" in *,*|*\"*) usage ;; esac

offline() {
    docker run --rm --pull=never --network=none --read-only --cap-drop=ALL \
        --security-opt=no-new-privileges --pids-limit=48 --memory=256m --cpus=1 \
        --user=65534:65534 --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m \
        --env PYTHONDONTWRITEBYTECODE=1 \
        --mount "type=bind,source=$root/plugins/exoverse/bin,target=/exoverse,readonly" \
        --mount "type=bind,source=$source_file,target=/input.json,readonly" \
        "$image_id" "$@"
}

case "$mode" in
    run)
        [ "$#" -eq 3 ] || usage
        offline /bin/sh -ec 'python /exoverse/exoverse-plugin workflow run /input.json --out /tmp/evidence.json >/dev/null; cat /tmp/evidence.json'
        ;;
    verify)
        [ "$#" -eq 4 ] || usage
        offline python /exoverse/exoverse-plugin workflow verify /input.json --sha256="$4"
        ;;
    *) usage ;;
esac
