# Scale and cost estimate: running this approach over the full ISA manual

Everything in this repo so far runs on curated snippets (2 challenge snippets,
13 benchmark cases, 3 robustness cases). This estimates what it costs to run
the same v3 prompt over the *entire* current privileged + unprivileged ISA
manual, using real measurements of the manual and real current Anthropic
pricing (not guessed).

## Real measurements (`ext/riscv-isa-manual/src/{priv,unpriv}`)

```
Files (.adoc):        147
Total lines:           52,230
Total words:          284,854
Total bytes:        2,046,839
Existing [#norm:...] tags: 1,796
Level-3+ section headers (====, =====, ======): 845
```

`845` sections is the natural chunking unit — one API call per section, the
same granularity as the hand-picked snippets used elsewhere in this repo
(cross-check: `284,854 words / 845 sections ≈ 337 words/section`, in the
same range as the challenge's own two example snippets).

**Not included:** the Debug Specification (governs Sdtrig/`dcsr`) is not
vendored in this submodule at all -- confirmed while sourcing benchmark case
#6/#14 (see `benchmark/cases/`). Crypto extension prose (`unpriv/crypto.adoc`,
`zk.adoc`, `zbkb.adoc`) exists but has zero corresponding parameter YAMLs in
the live repo today. Both are out of scope for this estimate.

## Per-call token cost (measured, not estimated)

The actual v3 prompt (template + vendored `param_schema.json` + few-shot
example, everything except the snippet itself) was rendered and measured
directly:

```
$ python3 -c "..."  # see git history for the exact script
Fixed template+schema+few-shot overhead: 2,902 chars (~725 tokens at 4 chars/token)
```

This ~725-token block is **identical on every call** -- it's exactly what
prompt caching is for.

## Extrapolating to all 845 sections

Using a standard ~1.3-1.5 tokens/word heuristic for English/AsciiDoc prose
(*approximate -- the accurate way to measure this is Anthropic's
`count_tokens` endpoint against the real corpus, which needs an API key we
don't have configured here; treat these as order-of-magnitude, not billing-grade*):

- Manual content: 284,854 words -> **~370,000-430,000 tokens** total across all 845 sections
- Fixed template overhead if resent on every call: 845 x 725 -> **~613,000 tokens**
- Output per call: estimated from this repo's own real results (`results/`,
  `benchmark/results/`) -- most sections produce 0-1 parameters, a few
  produce 2-3; blended average **~150-250 tokens/call** -> **~130,000-210,000 tokens** total output

### Naive (no prompt caching) -- one full pass, one model

| | Input tokens | Output tokens |
|---|---|---|
| Content (unique per section) | ~400,000 | -- |
| Template (resent every call) | ~613,000 | -- |
| Output | -- | ~170,000 |
| **Total** | **~1,013,000** | **~170,000** |

### With prompt caching (5-min TTL, calls run back-to-back)

The ~725-token template is identical every call, so after the first call it's
a cache read (~0.1x price) instead of full price:

```
613,000 template tokens -> ~1 real write (725) + 844 cache-reads at 0.1x
                         ≈ 725 + 844 x 72.5 ≈ 61,900 effective tokens
```

| | Input tokens (effective) | Output tokens |
|---|---|---|
| Content (full price, unique) | ~400,000 | -- |
| Template (cached after call 1) | ~62,000 | -- |
| **Total** | **~462,000** | **~170,000** |

## Cost per model, one full pass over the current manual

Current published pricing (verified via the `claude-api` skill, not
estimated -- see table below for source):

| Model | Input $/MTok | Output $/MTok | Naive (no cache) | With caching |
|---|---|---|---|---|
| Claude Sonnet 5 | $3.00 | $15.00 | ~$5.60 | ~$3.94 |
| Claude Opus 4.8 | $5.00 | $25.00 | ~$9.32 | ~$6.56 |
| Claude Haiku 4.5 | $1.00 | $5.00 | ~$1.86 | ~$1.31 |

(Sonnet 5 also has an introductory rate of $2/$10 per MTok through
2026-08-31, which would lower its column further -- not used here since it's
temporary.)

**Sonnet + Opus together, one full pass each over the entire current ISA
manual: ~$10.50 with basic prompt caching, ~$14.90 without it.** That's the
number I can actually verify. Adding a GLM-4.6 leg would add to that total,
but I don't have a verified current per-token price for it -- the
`claude-api` skill only covers Anthropic pricing, and I'm not citing a
Z.ai figure without checking their live pricing page first. Order of
magnitude, GLM would likely land under either Anthropic leg on price, but
that's a guess I'm flagging as a guess, not a number I'm standing behind.

## The actual implication

Cost is not the constraint on scaling this approach. ~$4-9 for a full pass
over the whole manual means the real bottleneck for a production pipeline is
everything this repo has actually been testing: grounding discipline (§4 of
the main README), schema-type fidelity (§6, the 69% number), and markup
robustness (§7) -- not API spend. A pipeline that runs 10-20 verification
passes per section to drive up precision is still cheap in absolute terms.
