# RISC-V Architectural Parameter Extraction -- Coding Challenge

Submission for the LFX Fall 2026 mentorship *"AI-assisted extraction of
architectural parameters from RISC-V specifications"* (Parameter SIG /
[riscv/riscv-unified-db](https://github.com/riscv/riscv-unified-db)).

The task: write prompts that extract architectural parameters from ISA
Manual excerpts, where a parameter is signaled by optionality language
("may/might/should", "optional/optionally",
"implementation-defined"/"implementation-specific"), deal explicitly with
model hallucination, and produce results as schema-shaped YAML.

## 1. Models used

| Model | Provider | Context window | Role |
|---|---|---|---|
| Claude Sonnet 5 (`claude-sonnet-5`) | Anthropic | 200K tokens | Run -- results in `results/claude-sonnet-5/` |
| Claude Opus 4.8 (`claude-opus-4-8`) | Anthropic | 200K tokens | Run -- results in `results/claude-opus-4-8/`; frontier proprietary comparison leg |
| GLM-4.6 | Z.ai (Zhipu) | ~128K tokens | Run -- results in `results/glm-4.6/`; open-weight comparison leg (exact UI version string to be confirmed) |

Long context matters more than it looks for this task: real ISA Manual
excerpts often split a parameter's trigger phrase ("implementation-specific")
and its constraint (e.g. "shall be uniform throughout the system") across
sentence or even section boundaries. A pipeline that pre-chunks the manual
into small windows can lose that link; feeding whole sections avoids it.

## 2. Prompt design and hallucination handling

Three prompt versions live in `prompts/`, each written to fix a concrete
failure of the last rather than as a menu of options:

- **[v1 -- naive](prompts/v1_naive.md):** ask for parameters directly, no
  anchoring. Over-triggers on anything that merely sounds technical --
  incorrectly flags fixed CSR encoding-convention text as if it were an
  implementation choice.
- **[v2 -- keyword-anchored](prompts/v2_keyword_anchored.md):** restrict
  extraction to sentences containing the five optionality phrases the
  challenge specifies, and require a **verbatim quote** as evidence for
  every extracted parameter. This is the core anti-hallucination lever: a
  quote either appears in the source text or it doesn't, which turns
  "did the model hallucinate" from a judgment call into a mechanical
  string-containment check.
- **[v3 -- schema-constrained](prompts/v3_schema_constrained.md):** adds
  the real `param_schema.json` (vendored in `schema/`, taken directly from
  `riscv/riscv-unified-db`) and a real merged parameter (`CACHE_BLOCK_SIZE`)
  as a few-shot example, and explicitly instructs the model that returning
  **zero parameters is a valid, expected answer**. Without this instruction,
  models are biased toward always finding *something*, which is its own
  hallucination risk on excerpts that describe fixed behavior.

v3 is what actually gets sent to a model by `scripts/extract.py`; v1/v2 are
kept as documentation of the iteration, not dead code.

### Mechanical grounding check

`scripts/validate.py` enforces the quote requirement automatically: every
result YAML must have a sibling `<NAME>.evidence.json` whose `quote` field
is checked for (whitespace-normalized) presence in the cited source
snippet. `tests/bad_examples/` contains two deliberately broken fixtures --
one with a fabricated quote, one that violates the schema -- to prove this
check fails closed rather than rubber-stamping everything:

```
$ python scripts/validate.py --results tests/bad_examples
[FAIL] tests/bad_examples/HALLUCINATED_QUOTE.yaml
    - quote for 'HALLUCINATED_QUOTE' not found (whitespace-normalized) in snippets/cmo_cache_block.txt (possible hallucination): '...'
[FAIL] tests/bad_examples/SCHEMA_INVALID.yaml
    - <root>: 'description' is a required property
    - name: 'schema_invalid_lowercase_name' does not match '^[A-Z][A-Z_0-9]*$'
    - quote for 'schema_invalid_lowercase_name' not found ...

2 file(s) checked, 4 error(s) total
```

## 3. Results

### Snippet 1 -- CMO cache blocks (Privileged Spec 19.3.1)

Three parameters extracted, in `results/claude-sonnet-5/`:

| Name | Type | Status |
|---|---|---|
| `CACHE_BLOCK_SIZE` | `integer` | **Already exists upstream** -- see [Ground-truth check](#ground-truth-check-against-the-live-repo) |
| `CACHE_CAPACITY` | `integer` | New -- no existing parameter covers this |
| `CACHE_ORGANIZATION` | `string` (placeholder) | New -- flagged as under-specified, see note below |

The source sentence bundles capacity, organization, and block size together
("both/all implementation-specific"), but they're modeled as **three
independent parameters**, not one. Nothing in the text ties their value
spaces together -- an implementation is free to pick any combination. This
mirrors real maintainer feedback from `riscv-unified-db` PR #2009, which
required splitting a single `PMLEN` parameter into three (one per
extension) for the identical reason: bundling independent implementation
choices into one parameter overclaims a shared constraint the spec doesn't
state.

`CACHE_ORGANIZATION` is deliberately modeled as an opaque `string` rather
than something more structured. The manual gives no enumerable value space
for "organization" (contrast with e.g. `PMLEN`, which has an explicit
`{0, 7, 16}` enum) -- it only says the execution environment must let
software discover it. Shipping a confident schema here would be a
different kind of hallucination (over-specifying a value space the spec
doesn't define). This is flagged in the YAML description as needing
Parameter SIG scoping before it's schema-complete, matching the real
precedent of maintainers deferring disputed modeling questions to the SIG
(e.g. `riscv-unified-db` issue #69, PR #1968).

#### Ground-truth check against the live repo

`CACHE_BLOCK_SIZE` already exists upstream at
[`spec/std/isa/param/CACHE_BLOCK_SIZE.yaml`](https://github.com/riscv/riscv-unified-db/blob/main/spec/std/isa/param/CACHE_BLOCK_SIZE.yaml),
gated on `Zicbom`/`Zicbop`/`Zicboz`. That gives a rare thing for this kind
of exercise: real ground truth to grade the extraction against, not just
self-assessment. Comparing:

- Both agree on `type: integer`, `minimum: 1`, and the `anyOf` extension
  gating.
- The upstream version's `maximum` is `18446744073709551615` (i.e.
  `2**64 - 1`) -- functionally no upper bound at all. The extraction here
  omits `maximum` entirely, which is the more honest representation of
  "the spec places no upper bound," rather than encoding "no bound" as a
  very large number.

### Snippet 2 -- CSR address mapping (Privileged Spec 2.1)

Zero parameters extracted -- see
[`results/claude-sonnet-5/csr_address_mapping.NO_PARAMETERS_FOUND.txt`](results/claude-sonnet-5/csr_address_mapping.NO_PARAMETERS_FOUND.txt).
This snippet contains no optionality language; every sentence describes a
fixed encoding convention every conformant implementation follows
identically. This is the negative control: a prompt that over-triggers on
"sounds technical" text would incorrectly extract 2-3 parameters here.

## 4. Model comparison: Sonnet 5 vs Opus 4.8 vs GLM-4.6

All three models were run on the identical v3 prompt (Claude models via
this environment; GLM-4.6 via a hosted playground at default settings).
Results in `results/claude-sonnet-5/`, `results/claude-opus-4-8/`, and
`results/glm-4.6/`.

| Dimension | Sonnet 5 | Opus 4.8 | GLM-4.6 |
|---|---|---|---|
| Groundedness (every param has a verbatim source quote) | pass | pass | pass |
| Recall on cache-block sentence | 3 candidates | 2 emitted + 1 explicitly declined | **1 only** (missed `CACHE_CAPACITY`) |
| Precision on CSR negative control | 0 (correct) | 0 (correct) | 0 (correct) |
| Schema conformity (passes `validate.py` first try) | pass | pass | pass |

No model hallucinated, all three correctly returned **zero** parameters on
the CSR negative control, and every emitted parameter passed schema +
grounding validation. The models split cleanly into two behaviors:

**The two frontier models (Sonnet, Opus) differ only on a judgment call.**
The source clause makes cache "organization" implementation-specific, so
the trigger is present. **Sonnet 5 emitted `CACHE_ORGANIZATION`** as a
parameter with an opaque `type: string` schema, flagged as needing SIG
scoping. **Opus 4.8 declined to emit it**
(see [`CACHE_ORGANIZATION.DECLINED.txt`](results/claude-opus-4-8/CACHE_ORGANIZATION.DECLINED.txt)),
arguing "organization" has no definable value space and an opaque-string
parameter validates nothing -- a schema-shaped false positive. Opus also
flagged that gating `CACHE_CAPACITY` on the CMO extensions is itself a
modeling question (any cache has a capacity regardless of CMO), which
Sonnet did not raise. Both extracted the two clean numeric parameters.

**The open-weight model (GLM-4.6) under-extracts.** GLM returned only
`CACHE_BLOCK_SIZE` -- and its output is near-identical to the few-shot
example it was shown (same `description` string, same `long_name: TODO`).
It **missed `CACHE_CAPACITY` entirely**, even though the evidence quote it
produced itself contains "The capacity ... of a cache ... implementation-
specific." This is textbook few-shot anchoring: the model reliably
reproduces the parameter it was shown as an example but fails to
generalize the extraction rule to the *novel* parameter sitting in the
same sentence. Crucially, everything GLM *did* emit was correct --
grounded, schema-valid, and it aced the negative control. Its failure mode
is not hallucination (low precision) but **omission (low recall)**.

**Why this matters for the project.** The Spring 2026 pipeline's documented
weakness was recall (36.8%), not precision -- and this n=2 probe reproduces
exactly that shape on the open-weight model: safe but incomplete. Two
concrete design implications follow:

1. **Model choice is a recall decision here, not a precision one.** All
   three models are trustworthy when they *do* extract; they differ in how
   much they *miss*. For a pipeline whose stated goal is quality/robustness,
   that argues for a frontier model on the extraction pass rather than
   trading recall for the open model's lower cost.
2. **Disagreement is a routing signal.** Where Sonnet and Opus split
   (`CACHE_ORGANIZATION`), the right pipeline behavior is to surface it for
   human/SIG review, not to auto-merge or average. The repo's own review
   culture backs the conservative call -- PR #2009 required splitting an
   over-broad parameter; issue #69 / PR #1968 show disputed modeling
   deferred to the Parameter SIG rather than merged speculatively.

## 5. Status -- open items

- **GLM version string:** the results are filed under `results/glm-4.6/`,
  but the exact version reported by the playground UI should be confirmed
  and the directory renamed if it differs (see
  [`results/glm-4.6/_raw_responses.txt`](results/glm-4.6/_raw_responses.txt)).
- **Sample size:** this is an n=2-snippet probe. The numbers here
  illustrate model *behavior differences*, not a benchmark score -- see §6.
- **API automation:** `scripts/extract.py` is written and ready
  (`ANTHROPIC_API_KEY` / `ZHIPU_API_KEY`) to reproduce all three legs
  automatically once keys are configured; the current results were produced
  by running the same prompt through each model directly.

## 6. Benchmark context

The Spring 2026 phase of this same effort (issue #1747, PRs #1765-#1832)
reported, after a metric-inflation bug fix, raw LLM recall of 36.8% and
classification accuracy of ~68% against its labeled set. That's the
number a "quality and implementation robustness" improvement (the Fall
proposal's stated goal) needs to beat. This submission's n=2 sample is too
small to claim a comparable score -- it's included here as the actual
target to validate against once this approach is run over a larger, real
sample of manual sections.

## How to run

```bash
python -m venv .venv
.venv/bin/pip install pyyaml jsonschema      # + anthropic / openai if calling APIs
python scripts/validate.py --results results/claude-sonnet-5   # should report 0 errors
python scripts/validate.py --results results/claude-opus-4-8   # should report 0 errors
python scripts/validate.py --results results/glm-4.6           # should report 0 errors
python scripts/validate.py --results tests/bad_examples        # should report 4 errors (proves the check has teeth)

# once ANTHROPIC_API_KEY / ZHIPU_API_KEY are set:
python scripts/extract.py --model claude-opus-4-8 --snippet snippets/cmo_cache_block.txt
python scripts/extract.py --model glm-4.6 --provider zhipu --snippet snippets/cmo_cache_block.txt
```

## Repo layout

```
prompts/    v1/v2/v3 prompt templates, each documenting the failure it fixes
snippets/   the two ISA Manual excerpts given in the challenge
schema/     param_schema.json + its dependencies, vendored from riscv/riscv-unified-db
scripts/    extract.py (calls a model), validate.py (schema + grounding check)
results/    extracted parameter YAML + evidence, per model
tests/      deliberately-broken fixtures proving validate.py fails closed
```

`schema/` is vendored from
[riscv/riscv-unified-db](https://github.com/riscv/riscv-unified-db)
(`spec/schemas/`), licensed BSD-3-Clause-Clear -- see
`schema/UPSTREAM-LICENSE-BSD-3-Clause-Clear.txt`.
