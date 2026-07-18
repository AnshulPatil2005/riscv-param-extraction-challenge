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

This version correctly abstains on the CSR snippet and correctly finds
both parameters in the cache-block snippet, but the field names/types are
free-form -- there's no guarantee the output actually matches the shape
`riscv-unified-db`'s real `param_schema.json` expects (e.g. it might name
a field `values` instead of putting an `enum` under `schema.items`). v3
fixes this by constraining the model to the live schema.
