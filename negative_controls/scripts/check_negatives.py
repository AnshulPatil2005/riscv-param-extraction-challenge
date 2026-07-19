#!/usr/bin/env python3
"""
Asserts that every case in negative_controls/cases/ produced ZERO extracted
parameters -- i.e. results/<model>/ contains a <CASE>.NO_PARAMETERS_FOUND.txt
sentinel and no <CASE>*.yaml file. These are hard negative controls: real
manual text containing "should"/"may" that does NOT describe an
implementation-configurable hardware behavior (software-facing advice,
performance recommendations). A prompt that pattern-matches on keyword
presence alone would over-trigger here; this is a checkable regression gate
against that failure mode, not just a prose claim.

Usage:
    python negative_controls/scripts/check_negatives.py --model claude-sonnet-5
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    args = ap.parse_args()

    cases_dir = ROOT / "negative_controls" / "cases"
    results_dir = ROOT / "negative_controls" / "results" / args.model
    cases = sorted(d.name for d in cases_dir.iterdir() if d.is_dir())

    failures = 0
    print(f"## Negative control check: {args.model}  ({len(cases)} cases)\n")

    for case in cases:
        sentinel = results_dir / f"{case}.NO_PARAMETERS_FOUND.txt"
        stray_yaml = list(results_dir.glob(f"{case}*.yaml"))

        ok = sentinel.exists() and not stray_yaml
        status = "PASS (correctly zero)" if ok else "FAIL"
        print(f"[{status}] {case}")
        if not sentinel.exists():
            print(f"    - missing sentinel: {sentinel.name}")
            failures += 1
        if stray_yaml:
            print(f"    - unexpected extraction(s): {[p.name for p in stray_yaml]} (false positive)")
            failures += 1

    print()
    print(f"{len(cases)} case(s) checked, {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
