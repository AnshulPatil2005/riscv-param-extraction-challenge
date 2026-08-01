# v1 -- naive baseline

Extract the architectural parameters from the following excerpt of the
RISC-V ISA Manual. An architectural parameter is any aspect of the
architecture that an implementation is allowed to choose rather than a
behavior the spec mandates fixed.

Return your answer as YAML, one document per parameter, with fields for
name, description, type, and constraints.

---
{snippet}
---

## Measured failure mode

Run against the CSR snippet (`csr_address_mapping.txt`) in a fresh context,
this prompt returns false positives in **every model tested** -- 4 from Opus 5,
3 from Sonnet 5, 1 from GLM-4.6. It has no anchor for what signals optionality,
so it pattern-matches "this text describes a technical rule" onto "this text
describes an implementation choice". Sonnet 5's output is self-refuting: it
emits `csr_address_space_width` as a parameter and records its constraint as
`Fixed at 12 bits`.

It also states no naming convention, and both Sonnet 5 and GLM-4.6 returned
free-form lowercase names that would fail `param_schema.json`.

Counts and quotes: [`results/grid/RAW_OUTPUTS.md`](../results/grid/RAW_OUTPUTS.md).
