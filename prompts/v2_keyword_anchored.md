# v2 -- keyword-anchored, quote-as-evidence

Extract architectural parameters from the excerpt below. Only extract
something as a parameter if the excerpt contains explicit optionality
language: "may", "might", "should", "optional"/"optionally", or
"implementation-defined"/"implementation-specific". Do not extract
anything whose optionality you have to infer -- it must be stated.

For each parameter found, output:
- `name`: a SCREAMING_SNAKE_CASE identifier
- `quote`: the exact sentence or clause (verbatim, copy-pasted, not
  paraphrased) from the excerpt that establishes this is a parameter
- `description`: what the parameter controls
- `type`: a plausible JSON-Schema-ish type (boolean, integer, string, enum)
- `constraints`: any bounds or enumerated legal values mentioned in the text

If the excerpt contains no optionality language, say so explicitly and
return no parameters. Do not force an answer.

---
{snippet}
---

## Why the `quote` field matters

Requiring a verbatim quote turns hallucination-checking into a mechanical
string-containment check instead of a judgment call: if `quote` doesn't
appear in the source text, the extraction is ungrounded by construction,
independent of whether it *sounds* plausible. `scripts/validate.py`
enforces this automatically.

## Remaining gap

Measured across three models in fresh contexts, this version **eliminates the
false positives** v1 produces on the CSR snippet: 0 parameters from all three,
with correct reasoning ("By convention" describes a fixed encoding rather than
granting implementation latitude). That is the real, attributable gain of the
whole prompt series.

On the cache snippet all three models return 3 parameters here. Two of those
three are wrong -- see [`CORRECTIONS.md`](../CORRECTIONS.md) 5 -- and no
keyword rule can fix that, because the trigger phrase genuinely governs all
three subjects in the sentence. Deciding it needs the repository, not the
sentence.

The field names and types are also free-form, with no guarantee they match the
shape `param_schema.json` expects. v3 addresses the second problem by
constraining the model to the live schema; it does not address the first.
