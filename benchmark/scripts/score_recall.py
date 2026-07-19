#!/usr/bin/env python3
"""
Recall benchmark: for each case in benchmark/cases/<NAME>/ (a real,
already-merged parameter's actual source manual text), checks whether
this run's manifest.json records a hit (an extraction was produced for
it), and separately reports schema.type fidelity vs. the ground truth.

Recall here means "did the pipeline recognize this passage warrants a
parameter", not "did it reproduce the exact same YAML" -- extractions
were produced independently, without copying ground_truth.yaml, so a
name/schema mismatch against ground truth does NOT count against recall,
only against the separate schema-fidelity metric.

IMPORTANT CAVEAT (also in README): these are all EXISTING, already-merged
repo parameters. A frontier model has plausibly seen riscv-unified-db
during pretraining, so this is not a blind held-out test -- read it as an
upper-bound sanity check ("can the pipeline re-derive known-good
parameters from their real source text"), not a true generalization
score. It also only measures recall (all 13 cases are known positives);
precision on negative/fixed-behavior text is covered separately in the
main results/ (the CSR snippet negative control).

Usage:
    python benchmark/scripts/score_recall.py --model claude-sonnet-5
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from validate import check_grounding, check_structural, load_validator  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    args = ap.parse_args()

    cases_dir = ROOT / "benchmark" / "cases"
    results_dir = ROOT / "benchmark" / "results" / args.model
    manifest_path = results_dir / "manifest.json"

    if not manifest_path.exists():
        print(f"no manifest at {manifest_path}")
        return 1

    manifest = json.loads(manifest_path.read_text())
    manifest.pop("_comment", None)

    validator = load_validator()
    cases = sorted(d.name for d in cases_dir.iterdir() if d.is_dir())

    hits = 0
    validation_passes = 0
    type_matches = 0
    scored = 0

    print(f"## Recall benchmark: {args.model}  ({len(cases)} cases)\n")
    print("| Case | Hit | Extracted as | Schema-valid+grounded | Type match |")
    print("|---|---|---|---|---|")

    for case in cases:
        entry = manifest.get(case)
        if entry is None:
            print(f"| {case} | **MISS** (not in manifest) | -- | -- | -- |")
            continue

        scored += 1
        hit = entry.get("hit", False)
        extracted_as = entry.get("extracted_as", "?")
        type_match = entry.get("schema_type_match", False)

        yaml_path = results_dir / f"{extracted_as}.yaml"
        passed = False
        if yaml_path.exists():
            errors = check_structural(validator, yaml_path) + check_grounding(yaml_path)
            passed = not errors

        hits += 1 if hit else 0
        validation_passes += 1 if passed else 0
        type_matches += 1 if type_match else 0

        print(
            f"| {case} | {'yes' if hit else 'NO'} | `{extracted_as}` | "
            f"{'pass' if passed else 'FAIL'} | {'match' if type_match else 'differs'} |"
        )

    print()
    print(f"Recall (existence): {hits}/{scored} = {hits/scored:.0%}")
    print(f"Schema+grounding valid (of hits): {validation_passes}/{hits}")
    print(f"Schema-type fidelity (of hits): {type_matches}/{hits} = {type_matches/hits:.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
