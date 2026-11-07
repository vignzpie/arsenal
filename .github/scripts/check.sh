#!/usr/bin/env bash
# Mechanical checks behind the review gate (see .github/CONTRIBUTING.md).
# Runs in CI on every PR, and locally from the repo root.

set -uo pipefail

usage() {
  cat <<EOF
Usage: .github/scripts/check.sh [--base <ref>]

Runs the gate's mechanical checks from the repo root:
  skills    skills-ref validate, license field, a README per skill, SKILL.md under 500 lines
  template  templates/skill/ passes the spec once <name> is filled in
  scripts   shellcheck for bash/sh, zsh -n for zsh
  index     the root README lists every tool, and its local links resolve
  private   commits since <ref> (and PR_TITLE / PR_BODY if set) have no
            private links, chat IDs, session trailers, home paths or email addresses

  --base <ref>  Where the branch starts, for the private check (default: origin/main).
                If the ref doesn't exist, the private check is skipped with a warning.

Exit codes: 0 all checks passed, 1 at least one check failed, 2 bad usage or
a required tool is missing (skills-ref, shellcheck, zsh).
EOF
}

base="origin/main"
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --base) [ $# -ge 2 ] || { echo "Error: --base needs a ref, e.g. --base origin/main" >&2; exit 2; }
            base="$2"; shift 2 ;;
    *) echo "Error: unknown option '$1'. Try --help." >&2; exit 2 ;;
  esac
done

if [ ! -f README.md ] || [ ! -d claude ]; then echo "Error: run this from the repo root." >&2; exit 2; fi
for tool in skills-ref shellcheck zsh; do
  command -v "$tool" >/dev/null 2>&1 || { echo "Error: '$tool' is not installed. See 'Checks you can run' in .github/CONTRIBUTING.md." >&2; exit 2; }
done

failed=0
fail() { echo "FAIL  $*"; failed=1; }
ok()   { echo "ok    $*"; }

# skills
for dir in claude/skills/*/; do
  dir="${dir%/}"
  if out="$(skills-ref validate "$dir" 2>&1)"; then ok "spec: $dir"; else fail "spec: $dir: $out"; fi
  if [ -f "$dir/README.md" ]; then ok "readme: $dir"; else fail "readme: $dir has no README.md"; fi
  if sed -n '/^---$/,/^---$/p' "$dir/SKILL.md" | grep -qE '^license:[[:space:]]*Apache-2\.0[[:space:]]*$'; then ok "license: $dir"; else fail "license: $dir/SKILL.md frontmatter needs 'license: Apache-2.0'"; fi
  lines="$(wc -l < "$dir/SKILL.md" 2>/dev/null || echo 0)"
  if [ "$lines" -lt 500 ]; then ok "size: $dir/SKILL.md ($lines lines)"; else fail "size: $dir/SKILL.md is $lines lines; the spec says under 500"; fi
done

# template: a skill started from templates/skill/ must pass the spec once <name> is filled in
if [ -f templates/skill/SKILL.md ]; then
  tmp="$(mktemp -d)"
  mkdir "$tmp/example-skill"
  sed 's/<name>/example-skill/g' templates/skill/SKILL.md > "$tmp/example-skill/SKILL.md"
  if out="$(skills-ref validate "$tmp/example-skill" 2>&1)"; then ok "template: templates/skill passes the spec"; else fail "template: templates/skill/SKILL.md fails the spec once <name> is filled in: $out"; fi
  rm -rf "$tmp"
  if sed -n '/^---$/,/^---$/p' templates/skill/SKILL.md | grep -qE '^license:[[:space:]]*Apache-2\.0[[:space:]]*$'; then ok "template: license"; else fail "template: templates/skill/SKILL.md frontmatter needs 'license: Apache-2.0'"; fi
  if [ -f templates/skill/README.md ]; then ok "template: README.md"; else fail "template: templates/skill has no README.md"; fi
else
  fail "template: templates/skill/SKILL.md is missing (CONTRIBUTING points new skills at it)"
fi

# scripts
while IFS= read -r f; do
  first="$(head -n 1 "$f")"
  case "$first" in
    *zsh*)       if zsh -n "$f" 2>/dev/null; then ok "zsh -n: $f"; else fail "zsh -n: $f"; fi ;;
    *bash*|*sh*) if shellcheck "$f" >/dev/null; then ok "shellcheck: $f"; else fail "shellcheck: $f (run: shellcheck $f)"; fi ;;
  esac
done < <(git ls-files | while IFS= read -r p; do
  case "$p" in *.sh|*.zsh|*.bash) echo "$p" ;; *) [ -x "$p" ] && head -c 2 "$p" | grep -q '#!' && echo "$p" ;; esac
done | sort -u)

# index
for tool in claude/skills/*/ claude/*; do
  tool="${tool%/}"
  [ "$tool" = claude/skills ] && continue
  if grep -qF "($tool" README.md; then ok "index: $tool"; else fail "index: $tool is missing from the root README"; fi
done
while IFS= read -r link; do
  path="${link%%#*}"; path="${path%/}"
  case "$path" in ''|*://*|mailto:*) continue ;; esac
  if [ -e "$path" ]; then ok "link: $link"; else fail "link: README.md points to '$link', which doesn't exist"; fi
done < <(grep -oE '\]\([^)]+\)' README.md | sed -E 's/^\]\(//; s/\)$//')

# private (this file is excluded from the diff scan: it holds the pattern itself)
pattern='claude\.ai/(code/)?(session|chat|share)|Claude-Session:|share\.google/|docs\.google\.com/|notion\.so/|discord(app)?\.com/channels/|(^|[^0-9])[0-9]{17,20}([^0-9]|$)|/home/[a-z]|/Users/[A-Za-z]|[[:alnum:]._%+-]+@[[:alnum:].-]+\.[a-z]{2,}'
if git rev-parse -q --verify "$base^{commit}" >/dev/null; then
  hits="$( { git log --format='%h %B' "$base..HEAD"; git diff "$base...HEAD" -- . ':!.github/scripts/check.sh'; printf '%s\n%s\n' "${PR_TITLE:-}" "${PR_BODY:-}"; } | grep -nE "$pattern" || true)"
  if [ -n "$hits" ]; then
    fail "private: possible private references since $base:"
    printf '%s\n' "$hits" | sed 's/^/        /'
  else
    ok "private: nothing matched since $base (this is a pattern check; read your own diff too)"
  fi
else
  echo "warn  private: base '$base' not found, skipped"
fi

exit "$failed"
