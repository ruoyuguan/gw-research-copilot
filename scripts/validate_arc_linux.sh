#!/usr/bin/env bash
set -euo pipefail

unset GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR

GWRC_ROOT="${GWRC_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ARC_REPO_ROOT="${ARC_REPO_ROOT:-$GWRC_ROOT/.local/upstream/arc}"
AC_FOUNDATION_REPO_ROOT="${AC_FOUNDATION_REPO_ROOT:-$GWRC_ROOT/.local/upstream/ac-foundation}"
ARC_COMMIT="${ARC_COMMIT:-b717cca9e1aec4436726b98c61e0ee27edcc0319}"
AC_FOUNDATION_COMMIT="${AC_FOUNDATION_COMMIT:-251c0f06bb45a4905d0b3f5e7649a40786fc2698}"
PAPER_ID="${PAPER_ID:-arXiv:0911.3380}"
SEARCH_TERM="${SEARCH_TERM:-isocurvaton}"
SECTION_TITLE="${SECTION_TITLE:-Conclusion}"
: "${AC_INSTALL_UV:?Set AC_INSTALL_UV to a verified Linux uv executable}"

for tool in git python3 "$AC_INSTALL_UV"; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool is unavailable: $tool" >&2
    exit 1
  fi
done

check_checkout() {
  local root="$1"
  local expected="$2"
  local actual
  actual="$(git -c safe.directory="$root" --git-dir="$root/.git" --work-tree="$root" rev-parse HEAD)"
  if [[ "$actual" != "$expected" ]]; then
    echo "Unexpected commit in $root: $actual (expected $expected)" >&2
    exit 1
  fi
  git -c core.fileMode=false -c safe.directory="$root" \
    --git-dir="$root/.git" --work-tree="$root" \
    diff --ignore-space-at-eol --quiet
  git -c core.fileMode=false -c safe.directory="$root" \
    --git-dir="$root/.git" --work-tree="$root" \
    diff --ignore-space-at-eol --cached --quiet
}

check_checkout "$ARC_REPO_ROOT" "$ARC_COMMIT"
check_checkout "$AC_FOUNDATION_REPO_ROOT" "$AC_FOUNDATION_COMMIT"
LAUNCHER="$ARC_REPO_ROOT/plugins/arc/bin/arc-runtime"
if [[ ! -f "$LAUNCHER" ]]; then
  echo "ARC runtime launcher is missing: $LAUNCHER" >&2
  exit 1
fi

if [[ -n "${VALIDATION_ROOT:-}" ]]; then
  if [[ -e "$VALIDATION_ROOT" ]]; then
    echo "VALIDATION_ROOT must be a new directory: $VALIDATION_ROOT" >&2
    exit 1
  fi
  mkdir -p "$VALIDATION_ROOT"
else
  VALIDATION_ROOT="$(mktemp -d /tmp/gwrc-arc-validation.XXXXXX)"
fi
RESULTS="$VALIDATION_ROOT/results"
mkdir -p "$RESULTS" "$VALIDATION_ROOT/tmp"

# Use native checkouts so Windows mount line endings cannot break Bash launchers.
git -c safe.directory="$ARC_REPO_ROOT" clone --quiet --no-checkout \
  "$ARC_REPO_ROOT" "$VALIDATION_ROOT/arc-source"
git -C "$VALIDATION_ROOT/arc-source" checkout --quiet --detach "$ARC_COMMIT"
git -c safe.directory="$AC_FOUNDATION_REPO_ROOT" clone --quiet --no-checkout \
  "$AC_FOUNDATION_REPO_ROOT" "$VALIDATION_ROOT/foundation-source"
git -C "$VALIDATION_ROOT/foundation-source" checkout --quiet --detach \
  "$AC_FOUNDATION_COMMIT"
LAUNCHER="$VALIDATION_ROOT/arc-source/plugins/arc/bin/arc-runtime"

export AC_PRODUCT_REPO_ROOT="$VALIDATION_ROOT/arc-source"
export AC_FOUNDATION_REPO_ROOT="$VALIDATION_ROOT/foundation-source"
export AC_INSTALL_SOURCE=local
export AC_INSTALL_PYTHON_BIN="${AC_INSTALL_PYTHON_BIN:-python3}"
export AC_HOME="$VALIDATION_ROOT/ac-home"
export AC_RUNTIME_HOME="$VALIDATION_ROOT/arc-runtime-home"
export ARC_PAPER_CACHE="$VALIDATION_ROOT/arc-paper-cache"
export AC_DOCUMENT_CACHE="$VALIDATION_ROOT/ac-document-cache"
export TMPDIR="$VALIDATION_ROOT/tmp"
export UV_CACHE_DIR="$VALIDATION_ROOT/uv-cache"
export PIP_CACHE_DIR="$VALIDATION_ROOT/pip-cache"
export UV_PYTHON_DOWNLOADS=never
export PYTHONNOUSERSITE=1
export VALIDATION_ROOT PAPER_ID ARC_COMMIT AC_FOUNDATION_COMMIT

mkdir -p "$AC_HOME" "$AC_RUNTIME_HOME" "$ARC_PAPER_CACHE" \
  "$AC_DOCUMENT_CACHE" "$TMPDIR" "$UV_CACHE_DIR" "$PIP_CACHE_DIR"
RUNTIME=(bash "$LAUNCHER")

echo "Installing the isolated ARC runtime under $VALIDATION_ROOT" >&2
"${RUNTIME[@]}" setup
"${RUNTIME[@]}" doctor > "$RESULTS/runtime-doctor.json"
"${RUNTIME[@]}" arc-paper --help > "$RESULTS/arc-paper-help.txt"
"${RUNTIME[@]}" arc-paper get-metadata "$PAPER_ID" \
  > "$RESULTS/metadata.json"
"${RUNTIME[@]}" arc-paper get-table-of-contents \
  --reference "$PAPER_ID" --source-format html > "$RESULTS/toc.json"
"${RUNTIME[@]}" arc-paper search-full-text \
  --reference "$PAPER_ID" --source-format html \
  --term "$SEARCH_TERM" --context-lines 1 > "$RESULTS/search.json"
"${RUNTIME[@]}" arc-paper get-section \
  --reference "$PAPER_ID" --source-format html "$SECTION_TITLE" \
  > "$RESULTS/section.json"

"$AC_INSTALL_UV" venv "$VALIDATION_ROOT/gwrc-venv" \
  --python "$(command -v python3)"
"$AC_INSTALL_UV" pip install \
  --python "$VALIDATION_ROOT/gwrc-venv/bin/python" "$GWRC_ROOT"

ADAPTER_LAUNCHER="$VALIDATION_ROOT/arc-runtime"
{
  printf '#!/bin/sh\n'
  printf 'exec bash "%s" "$@"\n' "$LAUNCHER"
} > "$ADAPTER_LAUNCHER"
chmod 755 "$ADAPTER_LAUNCHER"
export GWRC_ARC_RUNTIME="$ADAPTER_LAUNCHER"
GWRC="$VALIDATION_ROOT/gwrc-venv/bin/gwrc"
"$GWRC" doctor --json > "$RESULTS/gwrc-doctor.json"
"$GWRC" arc-metadata "$PAPER_ID" \
  --output-dir "$VALIDATION_ROOT/gwrc-arc-metadata" \
  > "$RESULTS/gwrc-metadata.json"

EVIDENCE_ROOT="${GWRC_ARC_EVIDENCE_DIR:-$GWRC_ROOT/.local/verification/arc-linux-$(basename "$VALIDATION_ROOT")}"
if [[ -e "$EVIDENCE_ROOT" ]]; then
  echo "Evidence directory already exists: $EVIDENCE_ROOT" >&2
  exit 1
fi
export GWRC_ARC_EVIDENCE_DIR="$EVIDENCE_ROOT"

python3 - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["VALIDATION_ROOT"])
results = root / "results"


def envelope(name):
    document = json.loads((results / name).read_text(encoding="utf-8"))
    assert document.get("schema_version") == "ac.command_result.v2", name
    assert document.get("status") == "completed", (name, document)
    assert document.get("error") is None, (name, document)
    data = document.get("data")
    assert isinstance(data, dict), name
    return data


runtime = json.loads((results / "runtime-doctor.json").read_text())
assert runtime["ready"] is True
metadata = envelope("metadata.json")
assert isinstance(metadata.get("title"), str) and metadata["title"].strip()
toc = envelope("toc.json")
entries = toc.get("entries")
assert isinstance(entries, list) and entries
search = envelope("search.json")
occurrences = search.get("occurrences")
assert isinstance(occurrences, list) and occurrences
section = envelope("section.json")
assert isinstance(section.get("text"), str) and section["text"].strip()
source = section.get("source")
assert isinstance(source, dict) and isinstance(source.get("document"), dict)

doctor = json.loads((results / "gwrc-doctor.json").read_text())
assert doctor["healthy"] is True
arc = next(check for check in doctor["checks"] if check["name"] == "ARC arc-paper")
assert arc["state"] == "available"
run = json.loads((root / "gwrc-arc-metadata" / "run.json").read_text())
assert run["status"] == "completed"
assert run["result"]["arc_response"]["status"] == "completed"

summary = {
    "schema_version": "gwrc.arc_linux_smoke.v1",
    "paper_id": os.environ["PAPER_ID"],
    "arc_commit": os.environ["ARC_COMMIT"],
    "foundation_commit": os.environ["AC_FOUNDATION_COMMIT"],
    "runtime_ready": True,
    "metadata_title": metadata["title"],
    "toc_entry_count": len(entries),
    "full_text_occurrence_count": len(occurrences),
    "section_title": section.get("title"),
    "source_document_reference_verified": True,
    "gwrc_runtime_adapter_completed": True,
    "validation_root": str(root),
    "evidence_root": os.environ["GWRC_ARC_EVIDENCE_DIR"],
}
(results / "summary.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
(results / "summary.md").write_text(
    "# ARC Linux validation\n\n"
    f"- Paper: `{summary['paper_id']}`\n"
    f"- Metadata title: {summary['metadata_title']}\n"
    f"- TOC entries: {summary['toc_entry_count']}\n"
    f"- Full-text occurrences: {summary['full_text_occurrence_count']}\n"
    f"- Section: {summary['section_title']}\n"
    "- Official runtime ready and GWRC runtime adapter completed.\n",
    encoding="utf-8",
)
PY

mkdir -p "$EVIDENCE_ROOT"
cp -r "$RESULTS" "$EVIDENCE_ROOT/results"
cp -r "$VALIDATION_ROOT/gwrc-arc-metadata" \
  "$EVIDENCE_ROOT/gwrc-arc-metadata"
echo "ARC validation evidence: $EVIDENCE_ROOT" >&2
cat "$EVIDENCE_ROOT/results/summary.json"
