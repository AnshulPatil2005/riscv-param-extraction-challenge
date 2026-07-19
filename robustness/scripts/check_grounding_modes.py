#!/usr/bin/env python3
"""
Robustness test: does grounding still hold when the SOURCE is raw,
untouched AsciiDoc (real [#norm:...]# tags, _italics_, *bold*, csr:x[]
macros intact) instead of hand-cleaned prose like snippets/ and
benchmark/cases/ use everywhere else in this repo?

This directly targets the documented failure mode from the Spring 2026
pipeline (PR #1832): tag/markup handling broke when the manual's
directory layout and inline markup shifted under it. Checks each
extraction's evidence quote against its raw_source.txt in TWO modes:

  naive:     same check as scripts/validate.py -- whitespace-normalized
             substring match only. This is what breaks when markup
             interrupts a quoted phrase (e.g. "_rs1_" vs "rs1").
  tag-aware: also strips [#norm:...]# / [#...]# tag wrappers, bare '#'
             closers, _italics_/*bold* markers, and inline
             prefix:target[] macros before comparing.

Usage:
    python robustness/scripts/check_grounding_modes.py --model claude-sonnet-5
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_asciidoc_markup(text: str) -> str:
    text = re.sub(r"\[#[^\]]*\]#", "", text)          # [#norm:tag]# opener
    text = re.sub(r"#", "", text)                      # bare # closer
    text = re.sub(r"_([^_]+)_", r"\1", text)            # _italics_
    text = re.sub(r"\*([^*]+)\*", r"\1", text)          # *bold*
    text = re.sub(r"\b\w+:([\w.]+)\[\]", r"\1", text)   # csr:xxx[] / ext:xxx[] / insn:xxx[]
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    args = ap.parse_args()

    results_dir = ROOT / "robustness" / "results" / args.model
    evidence_files = sorted(results_dir.glob("*.evidence.json"))
    if not evidence_files:
        print(f"no evidence files in {results_dir}")
        return 1

    print(f"## Grounding-mode comparison: {args.model}\n")
    print("| Case | Naive match | Tag-aware match |")
    print("|---|---|---|")

    naive_passes = 0
    tagaware_passes = 0
    total = 0

    for ev_path in evidence_files:
        evidence = json.loads(ev_path.read_text())
        for name, entry in evidence.items():
            total += 1
            quote = entry["quote"]
            source_path = ROOT / entry["source_file"]
            source_text = source_path.read_text()

            naive_ok = normalize_ws(quote) in normalize_ws(source_text)
            tagaware_ok = normalize_ws(strip_asciidoc_markup(quote)) in normalize_ws(
                strip_asciidoc_markup(source_text)
            )

            naive_passes += naive_ok
            tagaware_passes += tagaware_ok
            print(f"| {name} | {'pass' if naive_ok else '**FAIL**'} | {'pass' if tagaware_ok else '**FAIL**'} |")

    print()
    print(f"Naive grounding:     {naive_passes}/{total}")
    print(f"Tag-aware grounding: {tagaware_passes}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
