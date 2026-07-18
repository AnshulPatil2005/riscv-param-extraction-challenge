# v3 -- schema-constrained, few-shot, explicit-zero-is-valid

You are extracting architectural parameters from the RISC-V ISA Manual for
the `riscv/riscv-unified-db` project. Every parameter you output MUST
validate against this JSON Schema (draft-07), reproduced from the live
repository at `spec/schemas/param_schema.json`:

```json
{param_schema_json}
```

Rules:
1. Only extract a parameter if the excerpt contains explicit optionality
   language: "may", "might", "should", "optional"/"optionally", or
   "implementation-defined"/"implementation-specific". Do not infer
   optionality that isn't stated.
2. For every parameter, separately record (outside the YAML, as a second
   JSON object) the exact verbatim quote from the excerpt that justifies
   it, keyed by parameter name: `{"PARAM_NAME": {"quote": "...",
   "source_file": "snippets/<file>"}}`. If you cannot point to an exact
   quote, do not emit the parameter.
3. Returning zero parameters is a fully valid, expected answer for
   excerpts that describe fixed/mandatory behavior rather than
   implementation choices. Do not force a match to avoid an empty answer.
4. Follow the naming convention `^[A-Z][A-Z_0-9]*$`, matching existing
   parameters in the repo (e.g. `CACHE_BLOCK_SIZE`, `PMLEN`).

## Few-shot example (real, merged parameter from the repo)

```yaml
$schema: param_schema.json#
kind: parameter
name: CACHE_BLOCK_SIZE
description: "The observable size of a cache block, in bytes"
long_name: TODO
schema:
  type: integer
  minimum: 1
definedBy:
  extension:
    anyOf:
      - name: Zicbom
      - name: Zicbop
      - name: Zicboz
```

---
{snippet}
---

## Why this version is the one actually run

v1 and v2 are documented as prior iterations to show the failure modes
they fix. v3 is what `scripts/extract.py` actually sends to the model(s),
because its output is directly checkable by `scripts/validate.py` against
the real schema files vendored in `schema/`, and its evidence-quote
requirement is what the grounding check enforces mechanically rather than
by inspection.
