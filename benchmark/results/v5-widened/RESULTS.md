# v5: widening the rule-1 trigger list

`prompts/v5_widened_triggers.md` is v4 with rule 1 extended from five phrases to
thirteen, adding "can", "if present", "is allowed to"/"are allowed to" and
"is permitted to"/"are permitted to". Nothing else changed.

The clean re-run (`../clean-rerun/`) attributed five of six benchmark misses to
that list being too narrow, and predicted widening would recover four. It did -- and cost one. It also
posed the risk: the CSR negative control contains "the lowest privilege level
that **can** access the CSR", so "can" puts that control directly in danger.

## Precision: unchanged

| Excerpt | v4 (Opus 5 / Sonnet 5) | v5 (Opus 5 / Sonnet 5) |
|---|---|---|
| Cache block, correct answer 1 | 1 / 1 | 1 / 1 |
| CSR mapping, correct answer 0 | 0 / 0 | **0 / 0** |

Both models saw the newly whitelisted "can" and declined anyway. Opus 5:

> The only occurrence of a listed optionality keyword is "can" in "the lowest
> privilege level that can access the CSR", where "can" describes
> architecturally fixed accessibility semantics rather than an implementation
> choice, so it does not justify a parameter under Rule 1.

The trigger list is a gate, not the decision. Widening the gate did not widen
what got through.

## Recall: four of six misses recovered

| Case | v4 | v5 | Trigger that fired |
|---|---|---|---|
| ARCH_ID_VALUE | miss | **hit** `MARCHID` | "a value of 0 **can** be returned" |
| MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE | miss | **hit** `MISALIGNED_ATOMICITY_GRANULE_SIZE` | "This PMA, **if present**" |
| VECTOR_LS_WHOLEREG_MISALIGNED_LEGAL | miss | **hit** `WHOLE_REGISTER_MISALIGNED_EXCEPTION` | "Implementations **are allowed to** raise" |
| LRSC_MISALIGNED_BEHAVIOR | miss | **hit** `MISALIGNED_LRSC_ACCESS_FAULT` | "**can** be generated ... **should** not be emulated" |
| TIME_CSR_IMPLEMENTED | miss | miss | -- |
| VFREDUSUM_INACTIVE_NODE_ELEMENT_BEHAVIOR | miss | miss | -- |

Four recovered. But the seven v4 hits were also re-run, and one of them regressed.

## The regression: a superset prompt is not monotonic

All seven v4 hits were re-run under v5. Six held. One did not:

| Case | v4 | v5 |
|---|---|---|
| RESERVED_VSET_X0X0_VLMAX_CHANGE | hit `VSETVL_RESERVED_SETS_VILL` | **miss** |

Its trigger phrase is "Implementations **may** set vill in either case" -- "may"
was whitelisted in v4 and is still whitelisted in v5. The gate did not change for
this case. The model's judgement did:

> this "may" clause describes transient, per-execution behavior of the `vill`
> bit ... not a fixed architectural configuration knob analogous to `VLEN`,
> `PMLEN`, or `ASID_WIDTH` ... it's discretionary runtime behavior on an
> already-reserved code path, not a design-time parameter.

**This is the result worth keeping.** The reasonable assumption -- that widening a
whitelist can only add extractions, because the new list is a strict superset --
is false. A prompt is not a filter applied to text; it is context that shapes
judgement everywhere, including on cases whose trigger never changed. Lengthening
rule 1 appears to have made the model stricter about what counts as a parameter,
which cost a case that a purely lexical model of the prompt says could not move.

Had the seven hits been assumed rather than re-run, this submission would have
reported 11/13. The real number is 10/13.

## Corrected headline

| | v4 | v5 |
|---|---|---|
| Concept recall | 7 / 13 (54%) | **10 / 13 (77%)** |
| False positives, negative control | 0 | **0** |

Four recovered, one lost, net +3.

## Three misses remain, and they are one category

Neither survivor is a vocabulary failure now. Both accepted the trigger and
declined on judgement.

`TIME_CSR_IMPLEMENTED` -- the model took "can convert" as a trigger and then
rejected it:

> This is a statement about *how* an implementation may realize a fixed,
> mandatory piece of architectural behavior ... not a configurable architectural
> value ... just a choice of implementation technique.

`VFREDUSUM_INACTIVE_NODE_ELEMENT_BEHAVIOR` -- unchanged from v4: the passage
contains "may" twice, but the freedom is exercised per operator node rather than
fixed once per implementation, so there is no single value to record.

`RESERVED_VSET_X0X0_VLMAX_CHANGE` -- the regression above, declined as
per-execution behaviour rather than a design-time value.

All three are the same objection in different clothes: the excerpt grants
*behavioural* freedom, and the model declines to record behaviour as a
configuration value. UDB disagrees in all three cases, since all three are merged
parameters. That disagreement is the substance of what a parameter is, and no
keyword rule reaches it.

So widening the list moved the failure mode from **lexical to semantic**. What is
left is the question of what counts as a parameter at all -- the same question
`CORRECTIONS.md` 5 answers for cache capacity, and the one that cannot be settled
by any keyword rule.

## What was run

All 13 benchmark cases and both negative-control excerpts were re-run under v5,
every one in a fresh context with no tool access. Nothing here is assumed.
