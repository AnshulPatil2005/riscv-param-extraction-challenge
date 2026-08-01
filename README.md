# RISC-V Architectural Parameter Extraction -- Coding Challenge

![validate](https://github.com/AnshulPatil2005/riscv-param-extraction-challenge/actions/workflows/validate.yml/badge.svg)

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

### Snippet 1 -- CMO cache blocks (`unpriv/cmo.adoc` lines 86-92)

> The challenge document labels this passage "Privileged Spec 19.3.1". It is
> in the **unprivileged** manual. See [CORRECTIONS.md](CORRECTIONS.md).

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

- Both agree on `type: integer` and the `anyOf` extension gating.
- **My first pass got the schema wrong, and this is the useful finding.** It
  wrote `minimum: 1` with no upper bound. But the sentence it correctly
  quoted says "naturally aligned power-of-two (or NAPOT) range" -- the
  power-of-two constraint was in the text and went unencoded. Upstream
  [PR #2189](https://github.com/riscv/riscv-unified-db/pull/2189) (merged)
  now expresses exactly that as an enum of powers of two.
  `results/claude-sonnet-5/CACHE_BLOCK_SIZE.yaml` is corrected to match; see
  [CORRECTIONS.md](CORRECTIONS.md).
- The lesson is the limit of grounding: the quote was genuine, the source
  reference was checkable, and `validate.py` passed. Grounding tests where a
  sentence came from, not whether the model modelled it properly.

### Snippet 2 -- CSR address mapping (Privileged Spec 2.1)

Zero parameters extracted -- see
[`results/claude-sonnet-5/csr_address_mapping.NO_PARAMETERS_FOUND.txt`](results/claude-sonnet-5/csr_address_mapping.NO_PARAMETERS_FOUND.txt).
This snippet contains no optionality language; every sentence describes a
fixed encoding convention every conformant implementation follows
identically. This is the negative control: a prompt that over-triggers on
"sounds technical" text would incorrectly extract 2-3 parameters here.

## 4. Prompt x model ablation (3 prompts x 3 models)

Three prompt versions against three models, on both snippets. Every Claude cell
ran in a **fresh context with no conversation history and no tool access**
(`tool_uses: 0` on all six); GLM-4.6 cells were run in fresh playground chats.
The snippet text is byte-identical across v1/v2/v3, so instruction wording is
the only variable within a column. Raw outputs:
[`results/grid/RAW_OUTPUTS.md`](results/grid/RAW_OUTPUTS.md).

Parameters emitted, in the order **Opus 5 / Sonnet 5 / GLM-4.6**:

| Prompt | Cache-block snippet | CSR snippet (negative control) |
|---|---|---|
| v1 naive | 4 / 3 / 3 | **4 / 3 / 1 -- all false positives** |
| v2 keyword-anchored | 3 / 3 / 3 | 0 / 0 / 0 -- all correct |
| v3 schema-constrained | 1 / 1 / 1 | 0 / 0 / 0 -- all correct |

### The negative control is the clean result

v1 fabricates parameters out of a fixed encoding table in **every** model:

- **Opus 5** reasoned that because `00`, `01` and `10` all denote read/write,
  "the choice among them is an additional degree of freedom".
- **Sonnet 5** emitted `csr_address_space_width`, then recorded its constraint
  as `Fixed at 12 bits`.
- **GLM-4.6** emitted `implemented_csr_count`, justified by "the spec ... does
  not mandate that all be implemented" -- a sentence not present in the snippet.

Requiring *stated* optionality plus a verbatim quote removes all of it: v2 and
v3 return zero here in every model. **This is the one gain in the grid that is
real and attributable.**

### The cache column cannot measure v3

Those counts read as steady improvement, 4 -> 3 -> 1. They are not. **v3 is the
only version carrying a few-shot example, and that example is
`CACHE_BLOCK_SIZE` -- the answer to this snippet.**

| Model | v3 output, cache snippet | Copied from the example? |
|---|---|---|
| GLM-4.6, run 1 | 1 param | **byte-identical**, including `long_name: TODO` |
| GLM-4.6, run 2 | 1 param | `description` prefix verbatim, then extended |
| Sonnet 5 | 1 param | `long_name` + `description` verbatim |
| Opus 5 | 1 param | no -- own wording, own rationale |
| Opus 4.8 | 2 params + 1 declined | no -- own wording, own rationale |

So the v2 -> v3 drop **cannot be credited to the schema constraint or to the
explicit permission to return zero**; it is confounded with answer leakage.
Only the two Opus runs demonstrably reasoned. Opus 5, with no repository
access, called cache capacity and organization "software-discoverable
microarchitectural properties with no architecturally observable behavior" --
independently reproducing the argument in [`CORRECTIONS.md`](CORRECTIONS.md) 5.

**Fix:** the few-shot example must be drawn from a passage that is not in the
test set.

### This corrects an earlier reading

An earlier version of this section concluded that GLM-4.6 "under-extracts",
"missed `CACHE_CAPACITY` entirely", and that model choice here is "a recall
decision" favouring a frontier model. The grid disproves that. Under v1 and v2,
GLM returns **3 parameters** on the cache snippet -- exactly like Sonnet 5 and
Opus 5. It is not a low-recall model; it was anchored by the example. And
`CACHE_CAPACITY` is not a parameter to have missed: see
[`CORRECTIONS.md`](CORRECTIONS.md) 5.

### Reproducibility caveat

The runs under `results/claude-sonnet-5/` and siblings were produced inside a
working conversation rather than a fresh one. Re-run cleanly, **Sonnet 5 on v3
returns 1 parameter for the cache snippet where the recorded run returned 3** --
same model, same prompt, different context, different answer. The grid
supersedes them as the measurement; they are kept as records of what was
originally produced.

## 5. Status -- open items

- **GLM version string:** the results are filed under `results/glm-4.6/`,
  but the exact version reported by the playground UI should be confirmed
  and the directory renamed if it differs (see
  [`results/glm-4.6/_raw_responses.txt`](results/glm-4.6/_raw_responses.txt)).
- **Sample size:** the model comparison in §4 is an n=2-snippet probe --
  it illustrates model *behavior differences*, not a benchmark score. §6
  below is a separate, larger (n=13) recall benchmark that gets closer to
  an actual number, with its own caveats.
- **API automation:** `scripts/extract.py` is written and ready
  (`ANTHROPIC_API_KEY` / `ZHIPU_API_KEY`) to reproduce all three legs
  automatically once keys are configured; the current results were produced
  by running the same prompt through each model directly.

## 6. Recall benchmark (n=13, real merged parameters)

The comparisons above are n=2. `benchmark/` is a larger, more real test:
13 parameters that are already merged into `riscv-unified-db`, each
re-paired with the *actual* ISA Manual prose it was derived from (found
and independently verified against `ext/riscv-isa-manual` -- see
`benchmark/cases/<NAME>/source.txt` and `ground_truth.yaml`). Two more
candidates were investigated and deliberately excluded (`TRAP_ON_ECALL_FROM_VS`,
`MTVEC_ILLEGAL_WRITE_BEHAVIOR`) because their only findable source passage
was generic boilerplate, not text specific enough to count as solid ground
truth -- logged here rather than silently dropped.

The v3 prompt was run against each of the 13 raw passages independently,
**without copying the answer** -- extraction names, descriptions, and
schema choices were composed fresh from the source text alone, so a
mismatch against the real YAML doesn't count against recall, only against
a separate schema-fidelity metric:

```
$ python benchmark/scripts/score_recall.py --model claude-sonnet-5
Recall (existence): 13/13 = 100%
Schema+grounding valid (of hits): 13/13
Schema-type fidelity (of hits): 9/13 = 69%
```

Every one of the 13 known-parameter passages was correctly recognized as
warranting a parameter, and every extraction is schema-valid and grounded
in a real quote. The **type-fidelity** number (69%) is the more honest
signal: on 4/13 cases the extraction chose a different value-shape than
the merged parameter (e.g. boolean vs. enum) -- same underlying constraint
identified, different modeling choice. That's consistent with the earlier
finding that *detecting* a parameter is the easy part; *modeling its value
space* is where real judgment (and disagreement) lives.

**Read this number carefully -- it is not a blind benchmark.** All 13
cases are parameters that already exist in a public repository a frontier
model has plausibly seen during pretraining. This measures "can the
pipeline mechanically re-derive a known-good parameter from its real
source text," which is a legitimate sanity check (the mechanics --
grounding, schema conformity, trigger-language discipline -- are real and
verified), but it is an upper bound, not a generalization estimate. A true
blind test needs source text with no existing answer to leak from --
candidates for that are the ~230 unresolved gaps the Spring pipeline
flagged, or newly-drafted spec text not yet in any repo. It is also not
comparable to the Spring pipeline's reported recall (69.7% raw / 88.4%
classification on v2): that was measured across the whole manual against a
185-parameter ground truth, this is 13 hand-picked cases. The two numbers
are not measuring the same thing, and treating this as beating that would be
exactly the kind of overclaim the rest of this submission argues against.

## 7. Robustness to raw, untouched spec markup

Every case above uses hand-cleaned prose -- real text, but with AsciiDoc
markup (`[#norm:...]#...#` tags, `_italics_`, inline `csr:x[]` macros)
stripped out for readability. That cleaning is exactly what the Spring 2026
pipeline's own failure mode (PR #1832) was about: tag/markup handling broke
when the manual's structure shifted under it. `robustness/` tests the same
extraction against **raw, untouched** source -- three passages pulled
directly from `ext/riscv-isa-manual` with zero cleanup, including one
(`CACHE_BLOCK_SIZE`) that's the exact same underlying sentence as the
challenge's own snippet, so the only variable is markup presence.

```
$ python robustness/scripts/check_grounding_modes.py --model claude-sonnet-5
| Case | Naive match | Tag-aware match |
|---|---|---|
| CACHE_BLOCK_SIZE | FAIL | pass |
| LRSC_ALIGNMENT_EXCEPTION_KIND | FAIL | pass |
| NUM_PMP_ENTRIES | pass | pass |

Naive grounding:     1/3
Tag-aware grounding: 3/3
```

The extraction itself was unaffected -- all three raw passages produced
correct, grounded parameters. But **naive substring grounding (the same
check `scripts/validate.py` uses) fails 2/3 of them**, because the model
naturally produces clean prose quotes that don't byte-match text
interrupted by `_italics_` markers or `[#norm:...]#` tag wrappers. Running
`scripts/validate.py` directly against `robustness/results/` reproduces
this: it reports the same 2 false "possible hallucination" failures.
`robustness/scripts/check_grounding_modes.py` adds a markup-stripping
normalization step before comparing and recovers all 3 -- a small,
concrete demonstration of exactly the class of bug that hurt the prior
pipeline, plus a working fix, not just a description of the risk. (One
case, `NUM_PMP_ENTRIES`, happened to pass naive grounding anyway -- its
tag boundaries landed on clean word breaks. Not every markup placement
breaks naive matching; this is why the test uses three real, differently-
structured passages instead of one.)

## 8. Hard negative controls

The CSR snippet (§3) is a clean negative control -- no optionality
language at all. `negative_controls/` is a harder test: two more real
passages that **do** contain the literal trigger words ("should" x3 in
each) but describe software-facing advice, not implementation-configurable
hardware behavior --

- `MTIP_SPURIOUS_INTERRUPT` -- guidance telling *software authors* to
  tolerate a spurious timer interrupt, not a hardware implementation choice
- `BRANCH_PREDICTION_ADVICE` -- compiler/software optimization advice
  about branch layout, not a configurable predictor parameter

```
$ python negative_controls/scripts/check_negatives.py --model claude-sonnet-5
[PASS (correctly zero)] BRANCH_PREDICTION_ADVICE
[PASS (correctly zero)] MTIP_SPURIOUS_INTERRUPT

2 case(s) checked, 0 failure(s)
```

Both correctly return zero parameters -- proof the extraction is keying on
"does this describe an implementation choice," not just "does this
sentence contain the word 'should'." A prompt that pattern-matches on
keyword presence alone would have over-triggered on both.

## 9. Scale and cost

All of the above runs on curated snippets. [`docs/scale_and_cost.md`](docs/scale_and_cost.md)
measures the real ISA manual (147 files, 284,854 words, 845 natural
section-sized chunks) and, using verified current Anthropic pricing (not
guessed), estimates the cost of a full pass: **Sonnet 5 + Opus 4.8
together, one full pass each over the entire current manual, costs on the
order of $10.50 with basic prompt caching, ~$14.90 without it.** The
takeaway: cost is not what limits this approach from scaling -- the
grounding, schema-fidelity, and markup-robustness questions tested above
are the actual bottleneck, not API spend.

## 10. What UDB already encodes, measured (no model involved)

Everything above tests an extractor against prose. These two analyses go the
other way and measure the repository itself. Both are pure functions of a
checkout -- no LLM, reproducible by anyone -- and both were run against a clean
`riscv/riscv-unified-db@df65361c` snapshot.

### CSR fields already name the parameters that govern them

`scripts/csr_param_index.py` reads the IDL attached to every CSR field
(`type()`, `sw_write()`, `reset_value()`) and classifies the field by what that
IDL branches on:

| Branches on | Fields | Share |
|---|---:|---:|
| a parameter | 848 | 88.1% |
| `implemented?(ExtensionName::...)` | 11 | 1.1% |
| a constant, i.e. nothing configurable | 104 | 10.8% |

963 CSR fields carry IDL; 92 of the 227 parameters are named directly inside
it. `mtvec.MODE` is the illustrative case: nothing in the manual's prose says
it is governed by `MTVEC_ACCESS`, `MTVEC_MODES` and
`MTVEC_ILLEGAL_WRITE_BEHAVIOR`, but its own `type()` and `sw_write()` name all
three.

The practical consequence is that a prose-only extractor is rediscovering,
badly, a mapping the repository already states in 848 places. The 104 fixed
fields are the false-positive class made concrete: a field there can still be
labelled WARL in the manual, and it still yields no parameter, because nothing
about it can differ between implementations. They are listed in
[`analysis/fixed_fields.md`](analysis/fixed_fields.md).

### 43 of 227 parameters are never read

`scripts/orphan_params.py` asks the reverse question: which parameters does the
ISA model actually consult?

| | Count | Share |
|---|---:|---:|
| read by some file under `spec/std/isa/` | 184 | 81.1% |
| **set in `cfgs/` but never read** | **39** | **17.2%** |
| not referenced anywhere | 4 | 1.8% |

The middle row is the interesting one. A configuration assigns those 39
parameters a value and nothing consults it, so two configs differing only in
that value describe the same machine. `MTVEC_BASE_ALIGNMENT_DIRECT` and
`MTVEC_BASE_ALIGNMENT_VECTORED` are both in it. The last four
(`HSTATEEN_CONTEXT_TYPE`, `HSTATEEN_CSRIND_TYPE`, `HSTATEEN_JVT_TYPE`,
`SSTATEEN_JVT_TYPE`) appear nowhere outside their own definition files at all;
`hstateen0.CONTEXT`, for instance, hardcodes `type: RW` and its `sw_write`
consults another CSR rather than the parameter that exists for it.

**This is not a defect list.** Much of the vector set looks defined ahead of the
IDL meant to consume it, which is a reasonable way to work. The point is that
"defined" and "has an effect" are different properties, the difference is
mechanically checkable, and it is currently invisible. Under the criterion that
a parameter must describe state that can differ between implementations, a
parameter nothing reads does not yet meet it. Full lists in
[`analysis/orphan_params.md`](analysis/orphan_params.md).

## How to run

```bash
python -m venv .venv
.venv/bin/pip install pyyaml jsonschema      # + anthropic / openai if calling APIs

python scripts/validate.py --results results/claude-sonnet-5   # should report 0 errors
python scripts/validate.py --results results/claude-opus-4-8   # should report 0 errors
python scripts/validate.py --results results/glm-4.6           # should report 0 errors
python scripts/validate.py --results tests/bad_examples        # should report 4 errors (proves the check has teeth)

python scripts/score.py --results-root results                 # auto comparison table + disagreement detector

python scripts/validate.py --results benchmark/results/claude-sonnet-5
python benchmark/scripts/score_recall.py --model claude-sonnet-5

python robustness/scripts/check_grounding_modes.py --model claude-sonnet-5   # naive vs tag-aware grounding
python negative_controls/scripts/check_negatives.py --model claude-sonnet-5  # hard negative controls

# repository analyses (section 10); need a riscv-unified-db checkout, no model
python scripts/csr_param_index.py --udb-root ../riscv-unified-db
python scripts/orphan_params.py  --udb-root ../riscv-unified-db --revision main

bash scripts/ci_check.sh   # everything above, in one gated pass -- same as CI

# once ANTHROPIC_API_KEY / ZHIPU_API_KEY are set:
python scripts/extract.py --model claude-opus-4-8 --snippet snippets/cmo_cache_block.txt
python scripts/extract.py --model glm-4.6 --provider zhipu --snippet snippets/cmo_cache_block.txt
```

## Repo layout

```
prompts/            v1/v2/v3 prompt templates + prompts/rendered/ (paste-ready, schema+snippet filled in)
snippets/            the two ISA Manual excerpts given in the challenge
schema/              param_schema.json + its dependencies, vendored from riscv/riscv-unified-db
scripts/             extract.py, validate.py, score.py, ci_check.sh, plus the two
                     repository analyses: csr_param_index.py and orphan_params.py
analysis/            generated output of those two (JSON + markdown), pinned to a revision
results/             extracted parameter YAML + evidence, per model, for the 2 challenge snippets
benchmark/           n=13 recall benchmark against real merged parameters
robustness/          raw-markup grounding test (naive vs tag-aware substring matching)
negative_controls/   hard negative controls -- real "should"/"may" text that isn't a parameter
docs/                scale_and_cost.md -- real manual measurements + verified pricing estimate
tests/               deliberately-broken fixtures proving validate.py fails closed
.github/workflows/   CI: runs scripts/ci_check.sh on every push
```

`schema/` is vendored from
[riscv/riscv-unified-db](https://github.com/riscv/riscv-unified-db)
(`spec/schemas/`), licensed BSD-3-Clause-Clear -- see
`schema/UPSTREAM-LICENSE-BSD-3-Clause-Clear.txt`.
