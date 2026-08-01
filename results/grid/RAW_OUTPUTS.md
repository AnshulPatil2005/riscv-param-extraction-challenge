# Prompt x model grid -- raw outputs

Every cell was run in a **fresh context with no conversation history and no tool
access** (verified: `tool_uses: 0` for all six Claude cells). Each context saw
only the rendered prompt text. The excerpt payload is byte-identical across
v1/v2/v3, so prompt wording is the only variable within a column.

Excerpt 1 = cache blocks (`snippets/cmo_cache_block.txt`).
Excerpt 2 = CSR address mapping (`snippets/csr_address_mapping.txt`) -- the
negative control, which should yield zero parameters.

Model rows are **Opus 5** and **Sonnet 5**. The pre-existing
`results/claude-opus-4-8/` is a different model version and is kept separately.

---

## v1 (naive) x Opus 5

**Excerpt 1 -- 4 parameters:** `CACHE_BLOCK_SIZE`, `CACHE_CAPACITY`,
`CACHE_ORGANIZATION`, `CACHE_INFO_DISCOVERY_MECHANISM`.

The fourth is not a value an implementation picks at all -- it is the existence
of a discovery mechanism, turned into a `type: string` parameter.

**Excerpt 2 -- 4 parameters (all false positives):** `IMPLEMENTED_CSRS`,
`CSR_ADDRESS`, `CSR_RW_ACCESSIBILITY`, `CSR_LOWEST_ACCESS_PRIVILEGE_LEVEL`.

It reasoned that because three encodings (00, 01, 10) all mean read/write, "the
choice among them is an additional degree of freedom" -- inventing optionality
from an encoding table.

## v1 (naive) x Sonnet 5

**Excerpt 1 -- 3 parameters:** `cache_block_size`, `cache_capacity`,
`cache_organization`.

Note the names are lowercase, violating `^[A-Z][A-Z_0-9]*$`. v1 states no naming
rule, so nothing enforced it.

**Excerpt 2 -- 3 parameters (all false positives):**
`csr_address_space_width`, `csr_rw_encoding_field`,
`csr_privilege_level_encoding_field`.

Self-contradictory: it lists `csr_address_space_width` as a parameter and then
records `Fixed at 12 bits` as its constraint.

---

## v2 (keyword-anchored) x Opus 5

**Excerpt 1 -- 3 parameters:** `CACHE_BLOCK_SIZE`, `CACHE_CAPACITY`,
`CACHE_ORGANIZATION`, each with a verbatim quote.

Correctly declined to treat the "shall be uniform" sentence as its own
parameter, recording it as a constraint on `CACHE_BLOCK_SIZE` instead.

**Excerpt 2 -- 0 parameters.** Correct. Explicitly noted that "By convention"
"describes an established fixed encoding rather than granting implementation
latitude", and that 00/01/10/11 "appear here as fixed encoding assignments, not
as legal values an implementation selects among".

## v2 (keyword-anchored) x Sonnet 5

**Excerpt 1 -- 3 parameters:** same three, same quote.

**Excerpt 2 -- 0 parameters.** Correct.

---

## v3 (schema-constrained, few-shot) x Opus 5

**Excerpt 1 -- 1 parameter:** `CACHE_BLOCK_SIZE`, with an independent rationale
for dropping the other two:

> Cache capacity and organization are also called implementation-specific, but
> they are software-discoverable microarchitectural properties with no
> architecturally observable behavior in this excerpt, so no separate parameter
> was emitted for them.

It also wrote its own `long_name` and `description` rather than reusing the
few-shot example's.

**Excerpt 2 -- 0 parameters.** Correct.

## v3 (schema-constrained, few-shot) x Sonnet 5

**Excerpt 1 -- 1 parameter:** `CACHE_BLOCK_SIZE` with
`long_name: TODO` and `description: "The observable size of a cache block, in
bytes"` -- **both copied verbatim from the few-shot example**, including the
literal placeholder `TODO`.

No rationale offered for omitting capacity or organization.

**Excerpt 2 -- 0 parameters.** Correct.

---

## v1 (naive) x GLM-4.6

**Excerpt 1 -- 3 parameters:** `Cache capacity`, `Cache organization`,
`Cache block size`. Free-form names; v1 states no naming rule.

**Excerpt 2 -- 1 parameter (false positive):** `implemented_csr_count`, with
`constraints: "0 <= value <= 4096"`.

Its justification is an inference the excerpt does not state: "The spec sets
aside space for up to 4,096 CSRs, but does not mandate that all be implemented."
Nothing in the passage says that.

## v2 (keyword-anchored) x GLM-4.6

**Excerpt 1 -- 3 parameters:** `CACHE_CAPACITY`, `CACHE_ORGANIZATION`,
`CACHE_BLOCK_SIZE`, each with a verbatim quote and correct SCREAMING_SNAKE_CASE.

**Excerpt 2 -- 0 parameters.** Correct.

## v3 (schema-constrained, few-shot) x GLM-4.6, second run

**Excerpt 1 -- 1 parameter:** `CACHE_BLOCK_SIZE`. The description opens with the
few-shot example's exact string, "The observable size of a cache block, in
bytes", then appends a sentence from the excerpt. `long_name` is filled in
properly this time rather than copying the example's literal `TODO`.

**Excerpt 2 -- 0 parameters.** Correct.

Compared against GLM's first v3 run, which was a byte-identical copy of the
example including `TODO`, the same model on the same prompt produced a verbatim
copy once and a partial copy once. The copied fragment is stable across both.

---

## Completed grid

Parameter counts. Excerpt 2 is the negative control; every non-zero entry there
is a false positive.

| Prompt | Cache: Opus 5 / Sonnet 5 / GLM-4.6 | CSR: Opus 5 / Sonnet 5 / GLM-4.6 |
|---|---|---|
| v1 naive | 4 / 3 / 3 | **4 / 3 / 1 -- all three wrong** |
| v2 keyword-anchored | 3 / 3 / 3 | 0 / 0 / 0 -- all three correct |
| v3 schema + few-shot | 1 / 1 / 1 | 0 / 0 / 0 -- all three correct |

Note on the pre-existing `results/` directory: those runs were produced inside a
working conversation rather than a fresh context. Re-run cleanly, Sonnet 5 on v3
returns 1 parameter for the cache excerpt where the recorded run returned 3. The
grid above supersedes them as the measurement; the originals are kept as records
of what was actually submitted at the time.

## The confound this exposes

v3's few-shot example **is `CACHE_BLOCK_SIZE`** -- the answer to excerpt 1. So
on that excerpt v3 cannot measure extraction: a model can score "correct" by
copying the worked example.

Three of the four models given v3 emitted a `CACHE_BLOCK_SIZE` that is wholly or
partly a copy of the example:

| Model | v3 output on excerpt 1 | Byte-identical to the few-shot example? |
|---|---|---|
| GLM-4.6 | 1 param | **yes, entirely** |
| Sonnet 5 | 1 param | `long_name` + `description` copied verbatim |
| Opus 5 | 1 param | no -- own wording, own rationale |
| Opus 4.8 | 2 params + 1 declined | no -- own wording, own rationale |

Only Opus 5 and Opus 4.8 demonstrably did the work.

**Consequence.** The apparent v2 -> v3 improvement on excerpt 1 (3 params -> 1)
is confounded with answer leakage and cannot be credited to schema constraint or
to the explicit permission to return zero. The *negative control* result is
clean, because the few-shot example is irrelevant there -- and that is where the
real, attributable gain sits: **v1 produces 3-4 false positives; v2 and v3
produce none.**

**Fix.** The few-shot example must be drawn from an excerpt that is not in the
test set. Until it is, excerpt 1 measures nothing for v3.
