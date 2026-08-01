# Clean-context re-run of the n=13 benchmark

Same v3 prompt, same 13 passages, same model family (Sonnet 5). The only
changed variable is **context**: each case ran in a fresh context with no
conversation history and no tool access (`tool_uses: 0` on all 13), so no run
could see another case, the ground truth, or any prior discussion.

The originally recorded run in `../claude-sonnet-5/` was produced inside a
working conversation. This re-run exists because `CORRECTIONS.md` 7 admits that
about the `results/` snippet runs, and the same objection applies here.

## Headline

| | Recorded run | Clean re-run |
|---|---|---|
| Concept recall | **13 / 13 (100%)** | **7 / 13 (54%)** |
| Exact name match | 1 / 13 | **0 / 13** |
| Schema-type match, of hits | 9 / 13 | **3 / 7** |

A 100% score on a 13-case benchmark should have been treated as a red flag
rather than a result. The clean figure lands in the same band as the Spring
pipeline's own published per-class recall (`NORM_DIRECT` 83%, `NORM_CSR_RW` 63%,
`NORM_CSR_WARL` 50%), which is a far more plausible place to be.

## Per case

| Case (ground truth) | Clean re-run | Extracted as |
|---|---|---|
| ARCH_ID_VALUE | miss | -- |
| LEGAL_VSTART | hit | `VSTART_ILLEGAL_INSN_ON_UNREACHABLE` |
| LRSC_MISALIGNED_BEHAVIOR | miss | -- |
| MISALIGNED_LDST_EXCEPTION_PRIORITY | hit | `LDST_AMO_MISALIGNED_EXCEPTION_PRIORITY` |
| MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE | miss | -- |
| MTVEC_ACCESS | hit | `MTVEC_SUPPORTED_VALUES` |
| NUM_PMP_ENTRIES | hit | `PMP_ENTRIES` |
| PMP_GRANULARITY | hit | `PMP_GRAIN` |
| RESERVED_VSET_X0X0_VLMAX_CHANGE | hit | `VSETVL_RESERVED_SETS_VILL` |
| TIME_CSR_IMPLEMENTED | miss | -- |
| VECTOR_FF_SEG_EXCEPTION_PARTIAL_LOAD | hit | `FOF_SEGMENT_PARTIAL_LOAD` |
| VECTOR_LS_WHOLEREG_MISALIGNED_LEGAL | miss | -- |
| VFREDUSUM_INACTIVE_NODE_ELEMENT_BEHAVIOR | miss | -- |

`NUM_PMP_ENTRIES` was the one exact name match in the recorded run. Clean, the
same passage came back as `PMP_ENTRIES`, so exact-name agreement is 0/13.

## Why it misses: the trigger list is too narrow

Five of the six misses are **vocabulary misses**, not reasoning failures. v3
rule 1 whitelists exactly five phrases -- "may", "might", "should",
"optional"/"optionally", "implementation-defined"/"implementation-specific" --
and instructs the model not to infer optionality beyond them. Real specification
prose routinely expresses implementation choice in other words:

| Case | Phrase the spec actually uses | On the whitelist? |
|---|---|---|
| ARCH_ID_VALUE | "a value of 0 **can** be returned" | no |
| TIME_CSR_IMPLEMENTED | "Implementations **can** convert reads" | no |
| MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE | "This PMA, **if present**" | no |
| VECTOR_LS_WHOLEREG_MISALIGNED_LEGAL | "Implementations **are allowed to** raise" | no |
| LRSC_MISALIGNED_BEHAVIOR | "**should** not be emulated" (subordinate clause) | yes, but rejected as not the governing verb |

The models were explicit about it. On the whole-register case:

> None of those exact terms appear ... The text uses "allowed to" ... If the
> intent is to treat "allowed to" as equivalent to "may" (which would be a
> defensible looser reading), the candidate parameter would be `SEW_MIN`.

It identified the right parameter and withheld it because the prompt told it to.

The sixth miss, `VFREDUSUM_INACTIVE_NODE_ELEMENT_BEHAVIOR`, is different and
more interesting: the passage does contain "may", twice, and the model still
declined -- arguing the freedom is per-operator and per-node rather than a
hart-wide value, so there is no single configuration value to record. That is a
judgement call about what a parameter *is*, not a vocabulary gap, and it is the
same class of question as the cache capacity case in `CORRECTIONS.md` 5.

## What this means

The keyword anchoring that makes v2 eliminate false positives (see README 4) is
the same mechanism that costs recall here. Precision and recall are being traded
against each other by one design decision -- the length of the whitelist -- and
the recorded 13/13 hid that trade entirely.

Widening the list is the obvious next experiment, and it is a *measurable* one:
add "can", "if present", "is allowed to", "is permitted to" and re-run. That
would very likely recover four of the six misses. Whether it reintroduces false
positives on the negative controls is exactly the question the harness exists to
answer, and it is not answered yet.

## Schema fidelity of the seven hits

| Case | Ground truth schema | Clean extraction | Match |
|---|---|---|---|
| NUM_PMP_ENTRIES | `integer`, enum `[0,16,64]` | `integer`, enum `[0,16,64]` | **exact** |
| MISALIGNED_LDST_EXCEPTION_PRIORITY | `string`, enum `[low,high]` | `string`, enum `[higher,lower]` | type + values |
| PMP_GRANULARITY | `integer`, 2..66 | `integer`, min 0 | type only |
| LEGAL_VSTART | `string`, enum `[1_stride,2_stride,4_stride,custom]` | `boolean` | no |
| RESERVED_VSET_X0X0_VLMAX_CHANGE | `string`, enum `[never,always,custom]` | `boolean` | no |
| VECTOR_FF_SEG_EXCEPTION_PARTIAL_LOAD | `string`, enum `[no_subsegment_loaded,custom]` | `boolean` | no |
| MTVEC_ACCESS | `string`, enum `[ro,rw]` | `array` of `integer`, minItems 1 | no |

`NUM_PMP_ENTRIES` is reproduced exactly, enum members included, from "Implementations
may implement zero, 16, or 64 PMP entries".

Three of the four mismatches are one systematic difference: where the prose offers a
binary choice the model writes a `boolean`, while UDB writes a `string` enum carrying a
`custom` member so implementations can do something beyond the named options. That
convention lives in the repository, not in the prose, and cannot be inferred from the
sentence.

The fourth is the interesting one. For `mtvec` the merged file has enum `[ro, rw]`;
the clean run returned an **array of legal integer values**, reading "the set of values
the register may hold can vary by implementation" as a WARL legal-value set. That is the
shape UDB uses elsewhere for exactly this kind of field (compare `MTVEC_MODES`). The
disagreement is about which aspect of the sentence to model, not about who read it
correctly.
