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
