#!/usr/bin/env python3
"""
Validates extracted parameter YAML files two ways:

1. Structural: each YAML file must validate against the *real*
   spec/schemas/param_schema.json from riscv/riscv-unified-db (vendored
   in schema/), using a full draft-07 validator with $ref resolution.
2. Grounding: every parameter must have a corresponding entry in the
   sibling `<snippet>.evidence.json` file, whose "quote" string appears
   verbatim in the source snippet text it claims to come from. This is
   the actual anti-hallucination check: an extraction with no traceable
   quote in the source, or a quote that doesn't match, fails.

Usage:
    python scripts/validate.py --results results/claude-sonnet-5
"""

import argparse
import json
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning)

import yaml
from jsonschema import Draft7Validator, RefResolver


def normalize_ws(text: str) -> str:
    """Collapse whitespace/newlines so a quote isn't penalized for not
    matching the source file's incidental line-wrap positions."""
    return re.sub(r"\s+", " ", text).strip()

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "schema"
SNIPPETS_DIR = ROOT / "snippets"


def load_validator() -> Draft7Validator:
    param_schema = json.loads((SCHEMA_DIR / "param_schema.json").read_text())
    schema_defs = json.loads((SCHEMA_DIR / "schema_defs.json").read_text())
    draft07 = json.loads((SCHEMA_DIR / "json-schema-draft-07.json").read_text())

    store = {
        "param_schema.json": param_schema,
        "param_schema.json#": param_schema,
        "schema_defs.json": schema_defs,
        "schema_defs.json#": schema_defs,
        "json-schema-draft-07.json": draft07,
        "json-schema-draft-07.json#": draft07,
    }
    resolver = RefResolver(base_uri="param_schema.json#", referrer=param_schema, store=store)
    return Draft7Validator(param_schema, resolver=resolver)


def check_structural(validator: Draft7Validator, path: Path) -> list[str]:
    doc = yaml.safe_load(path.read_text())
    errors = sorted(validator.iter_errors(doc), key=lambda e: e.path)
    return [f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors]


def check_grounding(path: Path) -> list[str]:
    """Every param name in `path` must appear as a key in the sibling
    .evidence.json, with a quote that is verbatim-present in the cited
    source snippet."""
    doc = yaml.safe_load(path.read_text())
    name = doc.get("name")
    evidence_path = path.with_suffix("").with_suffix(".evidence.json")
    errors = []

    if not evidence_path.exists():
        return [f"no evidence file found at {evidence_path.name} -- ungrounded extraction"]

    evidence = json.loads(evidence_path.read_text())
    entry = evidence.get(name)
    if entry is None:
        return [f"no evidence entry for parameter '{name}' in {evidence_path.name}"]

    quote = entry.get("quote", "")
    source_file = entry.get("source_file", "")
    source_path = ROOT / source_file
    if not source_path.exists():
        return [f"evidence cites source_file '{source_file}' which does not exist"]

    source_text = source_path.read_text()
    if normalize_ws(quote) not in normalize_ws(source_text):
        errors.append(
            f"quote for '{name}' not found (whitespace-normalized) in {source_file} "
            f"(possible hallucination): {quote!r}"
        )
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True, help="Directory of *.yaml result files")
    args = ap.parse_args()

    results_dir = Path(args.results).resolve()
    yaml_files = sorted(results_dir.glob("*.yaml"))
    if not yaml_files:
        print(f"no *.yaml files found in {results_dir}")
        return 1

    validator = load_validator()
    total_errors = 0

    for path in yaml_files:
        struct_errors = check_structural(validator, path)
        ground_errors = check_grounding(path)
        all_errors = struct_errors + ground_errors

        status = "PASS" if not all_errors else "FAIL"
        print(f"[{status}] {path.relative_to(ROOT)}")
        for e in all_errors:
            print(f"    - {e}")
        total_errors += len(all_errors)

    print()
    print(f"{len(yaml_files)} file(s) checked, {total_errors} error(s) total")
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
