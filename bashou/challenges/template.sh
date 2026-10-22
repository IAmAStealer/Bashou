#!/usr/bin/env bash
# What it does, in one line.
# Usage: name.sh FILE...

die() { printf '%s: %s\n' "${0##*/}" "$*" >&2; exit 1; }

main() {
  if (( $# < 1 )); then
    printf 'usage: %s FILE...\n' "${0##*/}" >&2
    exit 2
  fi
  local f
  for f in "$@"; do
    [[ -f $f ]] || die "not a file: $f"
    # your step here
  done
}

main "$@"
