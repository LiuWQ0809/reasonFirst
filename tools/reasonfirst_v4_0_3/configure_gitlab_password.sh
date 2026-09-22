#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -gt 1 ]; then
  echo "Usage: $0 [/path/to/reasonFirst]" >&2
  exit 2
fi

RF_DIR="${1:-$PWD}"
RF_DIR="$(cd "$RF_DIR" && pwd)"
[ -f "$RF_DIR/pyproject.toml" ] || { echo "Not a reasonFirst checkout: $RF_DIR" >&2; exit 1; }

CFG_DIR="$HOME/.config/gitlab-agent"
CFG="$CFG_DIR/.env"
mkdir -p "$CFG_DIR"
chmod 700 "$CFG_DIR"

if [ -e "$CFG" ]; then
  echo "Existing config found: $CFG" >&2
  echo "Refusing to overwrite it automatically. Back it up/remove it intentionally, then rerun." >&2
  exit 1
fi

printf 'GitLab base URL: '
IFS= read -r BASE_URL
printf 'GitLab username/email: '
IFS= read -r USERNAME
printf 'GitLab password: '
stty -echo
IFS= read -r PASSWORD
stty echo
printf '\n'
printf 'Allowed project (group/project, blank = all): '
IFS= read -r PROJECT

case "$BASE_URL" in
  https://*) ;;
  *) echo "GitLab URL must start with https://" >&2; exit 1 ;;
esac
[ -n "$USERNAME" ] || { echo "Username is required" >&2; exit 1; }
[ -n "$PASSWORD" ] || { echo "Password is required" >&2; exit 1; }
case "$PASSWORD" in
  *$'\n'*|*$'\r'*) echo "Password must not contain newlines" >&2; exit 1 ;;
esac
if [ -n "$PROJECT" ]; then
  case "$PROJECT" in
    */*) ;;
    *) echo "Project must be group/project, or leave blank for all accessible projects" >&2; exit 1 ;;
  esac
  REQUIRE_ALLOWLIST=true
