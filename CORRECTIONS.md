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
