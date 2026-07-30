#!/usr/bin/env python3
"""
Builds an index of which UDB parameters govern which CSR fields, by reading the
IDL functions attached to each field (type(), sw_write(), reset_value()).

The point: a parameter-extraction pipeline that reads only specification prose
is trying to rediscover information the repository already carries explicitly.
`mtvec.MODE` does not say in prose that it is governed by MTVEC_ACCESS,
MTVEC_MODES and MTVEC_ILLEGAL_WRITE_BEHAVIOR -- but its own type() and
sw_write() name all three. This script counts how often that is true.

Each field carrying at least one IDL function is classified by what those
functions branch on:

  parameterised   references a known parameter -> the parameter exists; a
                  candidate extracted from prose should be reconciled against
                  it rather than proposed under a new name
  extension_gated references implemented?(ExtensionName::...) and no parameter
                  -> behaviour follows from configuration, which UDB expresses
                  with definedBy; no parameter
  fixed           neither -> the ISA fixes it, so there is no implementation
                  choice and no parameter. This is the false-positive class:
                  a field here can still be labelled WARL in the manual.

No model is involved. The output is a function of the checkout alone.

Usage:
    python scripts/csr_param_index.py --udb-root /path/to/riscv-unified-db
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
PARAM_TOKEN = re.compile(r"\b[A-Z][A-Z0-9_]{3,}\b")
IMPLEMENTED = re.compile(r"implemented\?\s*\(")


def load_params(udb: Path) -> set:
    d = udb / "spec/std/isa/param"
    if not d.is_dir():
        sys.exit(f"no parameter directory under {udb}")
    return {p.stem for p in d.glob("*.yaml")}


def idl_bodies(field: dict):
    """Yield (key, body) for every IDL function attached to a field."""
    if not isinstance(field, dict):
        return
    for key, val in field.items():
        if isinstance(key, str) and "(" in key and isinstance(val, str):
            yield key, val


def walk_csrs(udb: Path, params: set):
    csr_dir = udb / "spec/std/isa/csr"
    rows, unparsed = [], 0
    for path in sorted(csr_dir.rglob("*.yaml")):
        try:
            doc = yaml.safe_load(path.read_text(errors="ignore"))
        except Exception:
            unparsed += 1
            continue
        if not isinstance(doc, dict):
            unparsed += 1
            continue
        csr = doc.get("name") or path.stem
        fields = doc.get("fields")
        if not isinstance(fields, dict):
            continue
        for fname, fdef in fields.items():
            bodies = list(idl_bodies(fdef))
            if not bodies:
                continue  # statically declared field, nothing to classify
            blob = "\n".join(b for _, b in bodies)
            refd = sorted(set(PARAM_TOKEN.findall(blob)) & params)
            if refd:
                kind = "parameterised"
            elif IMPLEMENTED.search(blob):
                kind = "extension_gated"
            else:
                kind = "fixed"
            rows.append({
                "csr": csr,
                "field": fname,
                "file": path.relative_to(udb).as_posix(),
                "functions": sorted(k.split("(")[0] for k, _ in bodies),
                "parameters": refd,
                "classification": kind,
            })
    return rows, unparsed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--udb-root", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=REPO / "analysis")
    args = ap.parse_args()

    udb = args.udb_root.expanduser().resolve()
    params = load_params(udb)
    rows, unparsed = walk_csrs(udb, params)

    by_kind = Counter(r["classification"] for r in rows)
    reverse = defaultdict(list)
    for r in rows:
        for p in r["parameters"]:
            reverse[p].append(f"{r['csr']}.{r['field']}")

    total = len(rows)
    print(f"parameters defined in UDB      : {len(params)}")
    print(f"CSR fields carrying IDL        : {total}")
    if unparsed:
        print(f"CSR files skipped (unparsable) : {unparsed}")
    print()
    print("field classification, by what its IDL branches on:")
    for kind in ("parameterised", "extension_gated", "fixed"):
        n = by_kind[kind]
        pct = (100.0 * n / total) if total else 0.0
        print(f"  {n:5}  {pct:5.1f}%  {kind}")
    print()
    print(f"parameters named by at least one CSR field : {len(reverse)} of {len(params)}")
    print()
    print("most-referenced parameters:")
    for p, fields in sorted(reverse.items(), key=lambda kv: -len(kv[1]))[:8]:
        print(f"  {len(fields):4}  {p}")

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "csr_param_index.json").write_text(json.dumps(
        {
            "counts": {
                "parameters": len(params),
                "fields_with_idl": total,
                "by_classification": dict(by_kind),
                "parameters_referenced": len(reverse),
            },
            "fields": rows,
            "parameter_to_fields": {k: sorted(v) for k, v in sorted(reverse.items())},
        },
        indent=2,
    ))

    fixed = [r for r in rows if r["classification"] == "fixed"]
    lines = [
        "# CSR fields whose IDL branches on nothing configurable",
        "",
        "Generated by `scripts/csr_param_index.py`. These fields carry IDL but",
        "reference neither a parameter nor `implemented?()`, so their behaviour is",
        "fixed by the ISA. Under the criterion that a parameter must describe state",
        "that *can differ between implementations*, none of these should yield a",
        "parameter -- including any that the manual labels WARL.",
        "",
        f"{len(fixed)} of {total} fields carrying IDL.",
        "",
        "| CSR | Field | Functions | Source |",
        "|---|---|---|---|",
    ]
    for r in fixed:
        lines.append(f"| `{r['csr']}` | `{r['field']}` | {', '.join(r['functions'])} | `{r['file']}` |")
    (args.out / "fixed_fields.md").write_text("\n".join(lines) + "\n")

    print()
    print(f"wrote {args.out / 'csr_param_index.json'}")
    print(f"wrote {args.out / 'fixed_fields.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
