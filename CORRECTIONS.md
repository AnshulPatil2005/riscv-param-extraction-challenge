# Corrections

Things this repository got wrong, and how they were found. Kept as a file
rather than quietly rewritten, because the whole argument of the submission is
that a result you cannot check is not worth much.

---

## 1. Source attribution: the cache-block passage is unprivileged, not privileged

**Was:** `snippets/cmo_cache_block.txt` and the README both labelled the
passage "RISC-V Privileged ISA Manual, Section 19.3.1", copying the label used
in the challenge document.

**Is:** the passage is in the **unprivileged** manual, at
`src/unpriv/cmo.adoc` lines 86-92, under "Memory and Caches" within the
"Background" section of the Cache Management Operations chapter. Verified
against the `ext/riscv-isa-manual` revision that `riscv-unified-db` pins.

**How it surfaced:** while building the raw-markup robustness test
(`robustness/cases/CMO_CACHE_BLOCK/`) I located the passage in the actual
submodule to get untouched AsciiDoc, and it was in `unpriv/`. That left this
repository internally inconsistent for a while: `robustness/` had the right
file, `snippets/` had the wrong one. The same mislabelling was raised
independently on
[riscv-unified-db#2053](https://github.com/riscv/riscv-unified-db/issues/2053).

**Why it matters more than a citation nit:** `scripts/validate.py` checks a
quote by locating it in the file the evidence names. Provenance that cannot be
resolved cannot be verified, so a wrong file reference silently disables the
one check that catches invented quotes.

---

## 2. `CACHE_BLOCK_SIZE` missed the power-of-two constraint

**Was:**

```yaml
schema:
  type: integer
  minimum: 1
```

and the README argued that omitting an upper bound was "more honest" than the
very large `maximum` the merged file carried at the time.

**Is:** an enum of powers of two. The quoted sentence says "naturally aligned
power-of-two (or **NAPOT**) range". That constraint was sitting in text the
extraction had already quoted correctly, and it went unencoded. Upstream
[PR #2189](https://github.com/riscv/riscv-unified-db/pull/2189), since merged,
replaces the old bound with exactly that enumeration.

**Why it matters:** this is the clearest available demonstration of what the
grounding check does *not* do. The quote was real, the source reference was
resolvable, `validate.py` passed, and the schema was still wrong. Grounding
establishes provenance. It says nothing about whether the model read the
sentence properly, and nothing about whether the extracted thing is a
parameter at all. Those are the harder questions.

Left unchanged: `results/claude-opus-4-8/` and `results/glm-4.6/` still
contain what those models actually produced. They are comparison records, not
the submitted answer, and editing them would destroy the thing they exist to
document.

---

## 3. Stale recall figure (36.8%)

**Was:** the README cited "36.8% recall" as the Spring 2026 pipeline's
documented result.

**Is:** 36.8% was a transient number that appeared mid-review inside
[PR #1792](https://github.com/riscv/riscv-unified-db/pull/1792) while a
metric-inflation bug was being fixed, and it was superseded within the same
PR. The reported results are v1 60.0% raw / 62.7% adjusted recall with 67.9%
classification accuracy, and v2 69.7% raw / 72.9% adjusted with 88.4%
classification accuracy
([PR #1793](https://github.com/riscv/riscv-unified-db/pull/1793)).

Per-class recall is the more informative figure and is much less even:
`NORM_DIRECT` 83%, `NORM_CSR_RW` 63%, `NORM_CSR_WARL` 50%.

**How it surfaced:** reading the phase PRs in full rather than their summary
tables. The lower number appears earlier in the thread than the corrected one,
so quoting the first figure found is easy to do and wrong.

---

## 4. Scope: the public Part I PRs are a snapshot, not current state

Not an error in this repository, but it changes how its comparisons should be
read. On
[#2053](https://github.com/riscv/riscv-unified-db/issues/2053) the Spring
mentee clarified that the pipeline being worked on now is internal, and that
PRs #1765-#1832 were its first version. Any measurement here against those
PRs, including the per-class figures above, describes that snapshot rather
than the live system.

---

## 5. The cache sentence yields one parameter, not three

**Was:** three parameters extracted from the cache-block passage --
`CACHE_BLOCK_SIZE`, `CACHE_CAPACITY`, `CACHE_ORGANIZATION`. The sentence marks
three things implementation-specific in one breath, so this is the obvious
reading, and it is what every model returns when the prompt does not hand it
the answer.

**Is:** one parameter and two recorded rejections.

The test that settles it is whether anything can read the value.
`CACHE_BLOCK_SIZE` is read by `cbo.clean`, `cbo.flush`, `cbo.inval`, `cbo.zero`
and `Zic64b` -- `cbo.zero` writes zeroes across a block of that size, so two
implementations differing in block size are distinguishable by running a
program. Nothing reads a cache's total capacity or its associativity, and it is
hard to see what could. They are implementation-specific in the ordinary sense,
and the execution environment lets software discover them, but they are not
observable architectural state.

**Corroboration:** Opus 5, run in a fresh context with no access to this
repository, independently declined both, calling them "software-discoverable
microarchitectural properties with no architecturally observable behavior".
Opus 4.8 had earlier declined `CACHE_ORGANIZATION` on the narrower ground that
it has no definable value space.

**Why it matters:** the trigger phrase appears once and governs three subjects.
A rule keyed on the phrase gets the count wrong; asking whether anything can
read the result gets it right. That question is answerable mechanically against
the repository, and not answerable from the sentence at all.

---

## 6. The v3 few-shot example leaks the answer to one of the two test snippets

**Was:** v3's improvement over v2 on the cache snippet -- 3 parameters down to
1 -- was reported as a gain from schema constraint plus explicit permission to
return zero.

**Is:** v3's few-shot example **is `CACHE_BLOCK_SIZE`**, the answer to that
snippet. A model can score "correct" there by copying the worked example, and
three of the five v3 runs did: GLM-4.6's first run was byte-identical to the
example including the literal placeholder `long_name: TODO`; its second run
copied the description's opening string; Sonnet 5 reproduced `long_name` and
`description` verbatim. Only the two Opus runs wrote their own text and gave a
reason.

**How it surfaced:** running the full 3x3 grid rather than v3 alone. Under v1
and v2 -- neither of which carries an example -- GLM-4.6 returns 3 parameters
on that snippet, the same as Sonnet 5 and Opus 5. Its earlier "1 parameter" was
never conservatism.

**What it invalidates:** the earlier README claim that GLM-4.6 under-extracts
and that model choice here is a recall decision. It also means the v2 -> v3 step
is unmeasured on this test set. The v1 -> v2 step survives, measured on the
negative control where the example is irrelevant: 4 / 3 / 1 false positives
down to 0 / 0 / 0.

**Fix:** draw the few-shot example from a passage that is not under test.

---

## 7. The recorded `results/` runs were not produced in a clean context

**Was:** `results/claude-sonnet-5/`, `results/claude-opus-4-8/` and
`results/glm-4.6/` were presented as the model comparison.

**Is:** they were produced inside a working conversation rather than a fresh
one. Re-run cleanly, Sonnet 5 on v3 returns 1 parameter for the cache snippet
where the recorded run returned 3 -- same model, same prompt, different context,
different answer.

`results/grid/` supersedes them as the measurement. They are kept, not
rewritten, as a record of what was originally produced; that is the same reason
the earlier entries in this file exist.

---

## 8. Predicted 11/13 for v5; measured 10/13

**Was:** the clean re-run predicted that widening rule 1's trigger list "would
very likely recover four of the six" misses. It did. The first write-up of v5
therefore reported **11/13**, re-running only the six misses and assuming the
seven v4 hits would hold. The reasoning: v5's whitelist is a strict superset of
v4's, so a case that triggered before must still trigger.

**Is:** **10/13**. All thirteen were re-run. Six of the seven hits held;
`RESERVED_VSET_X0X0_VLMAX_CHANGE` regressed, on a passage whose trigger --
"Implementations **may** set vill" -- is whitelisted in both versions. The gate
did not change for that case. The model's judgement did, declining it as
"transient, per-execution behavior ... not a design-time parameter".

**Why it matters:** the superset argument treats a prompt as a filter applied to
text. It is not. A prompt is context that shapes judgement everywhere, including
on cases whose rule was untouched, so a change that is lexically monotonic can be
behaviourally non-monotonic. This is the same class of mistake as 7 -- assuming a
measurement rather than making it -- caught the same way, by re-running instead
of reasoning about what the re-run would show.

