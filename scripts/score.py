#!/usr/bin/env python3
"""
Auto-generates the model comparison table from results/<model>/*.yaml,
instead of hand-writing it in the README. Also flags disagreements
between models on the same snippet -- pairs of models that extracted a
different set of parameter names from the same source_file.

Usage:
    python scripts/score.py --results-root results
    python scripts/score.py --results-root benchmark/results --cases benchmark/cases
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import check_grounding, check_structural, load_validator  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def load_model_dir(model_dir: Path):
    """Returns dict: source_file -> list of (name, yaml_path, passed: bool)."""
    validator = load_validator()
    by_source: dict[str, list] = defaultdict(list)

    for yaml_path in sorted(model_dir.glob("*.yaml")):
        doc_errors = check_structural(validator, yaml_path)
        ground_errors = check_grounding(yaml_path)
        passed = not (doc_errors + ground_errors)

        evidence_path = yaml_path.with_suffix("").with_suffix(".evidence.json")
        name = yaml_path.stem
        source_file = "?"
        if evidence_path.exists():
            evidence = json.loads(evidence_path.read_text())
            entry = evidence.get(name) or next(iter(evidence.values()), {})
            source_file = entry.get("source_file", "?")

        by_source[source_file].append((name, yaml_path, passed))

    # zero-parameter (negative control) sentinels
    for sentinel in sorted(model_dir.glob("*.NO_PARAMETERS_FOUND.txt")):
        snippet_stem = sentinel.name.split(".NO_PARAMETERS_FOUND")[0]
        # best-effort: find a snippets/ or benchmark/cases/ file matching the stem
        for candidate_dir in [ROOT / "snippets", ROOT / "benchmark" / "cases"]:
            for ext in (".txt",):
                candidate = candidate_dir / f"{snippet_stem}{ext}"
                if candidate.exists():
                    rel = str(candidate.relative_to(ROOT)).replace("\\", "/")
                    by_source.setdefault(rel, [])
                    break

    return by_source


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", default="results", help="Directory containing one subdir per model")
    args = ap.parse_args()

    results_root = (ROOT / args.results_root).resolve()
    model_dirs = sorted(d for d in results_root.iterdir() if d.is_dir())
    if not model_dirs:
        print(f"no model subdirectories found in {results_root}")
        return 1

    per_model = {d.name: load_model_dir(d) for d in model_dirs}

    all_sources = sorted({src for data in per_model.values() for src in data})

    print(f"## Comparison: {args.results_root}\n")
    header = "| Snippet | " + " | ".join(per_model.keys()) + " |"
    sep = "|---|" + "---|" * len(per_model)
    print(header)
    print(sep)

    total_emitted = defaultdict(int)
    total_passed = defaultdict(int)

    for src in all_sources:
        row = [Path(src).name]
        for model_name, data in per_model.items():
            entries = data.get(src, [])
            names = ", ".join(n for n, _, _ in entries) if entries else "(none)"
            fails = sum(1 for _, _, ok in entries if not ok)
            cell = names if not fails else f"{names} [{fails} FAIL]"
            row.append(cell)
            total_emitted[model_name] += len(entries)
            total_passed[model_name] += sum(1 for _, _, ok in entries if ok)
        print("| " + " | ".join(row) + " |")

    print()
    print("| Model | Params emitted | Passed validation |")
    print("|---|---|---|")
    for model_name in per_model:
        print(f"| {model_name} | {total_emitted[model_name]} | {total_passed[model_name]} |")

    # disagreement detection: same source_file, different name sets, across model pairs
    print("\n## Disagreements (same snippet, different parameter name sets)\n")
    found_any = False
    model_names = list(per_model.keys())
    for src in all_sources:
        name_sets = {m: {n for n, _, _ in per_model[m].get(src, [])} for m in model_names}
        union = set().union(*name_sets.values()) if name_sets else set()
        if not union:
            continue
        # flag any name not present in ALL models that emitted something for this source
        contested = {n for n in union if len({m for m in model_names if n in name_sets[m]}) < len(
            [m for m in model_names if name_sets[m]]
        )}
        if contested:
            found_any = True
            print(f"- **{Path(src).name}**:")
            for m in model_names:
                present = sorted(name_sets[m] & contested)
                if present:
                    print(f"    - {m} only/partial: {', '.join(present)}")

    if not found_any:
        print("(none -- all models that extracted anything for a given snippet agreed on names)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
