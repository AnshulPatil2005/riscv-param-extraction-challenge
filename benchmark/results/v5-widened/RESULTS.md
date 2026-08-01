# v5: widening the rule-1 trigger list

`prompts/v5_widened_triggers.md` is v4 with rule 1 extended from five phrases to
thirteen, adding "can", "if present", "is allowed to"/"are allowed to" and
"is permitted to"/"are permitted to". Nothing else changed.

The clean re-run (`../clean-rerun/`) attributed five of six benchmark misses to
that list being too narrow, and predicted widening would recover four. It also
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

**Recall 7/13 -> 11/13 (85%), with false positives unchanged at zero.**

## The two that remain are a different kind of miss

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

So widening the list moved the failure mode from **lexical to semantic**. What is
left is the question of what counts as a parameter at all -- the same question
`CORRECTIONS.md` 5 answers for cache capacity, and the one that cannot be settled
by any keyword rule.

## Caveat

Only the six v4 misses were re-run under v5; the seven v4 hits were not. v5's
trigger list is a strict superset of v4's, so a case that fired before still
fires, but model behaviour could shift for other reasons. 11/13 therefore
assumes those seven hold. The negative control was re-run in full.
