# v1 -- naive baseline

Extract the architectural parameters from the following excerpt of the
RISC-V ISA Manual. An architectural parameter is any aspect of the
architecture that an implementation is allowed to choose rather than a
behavior the spec mandates fixed.

Return your answer as YAML, one document per parameter, with fields for
name, description, type, and constraints.

---
{snippet}
---

## Observed failure mode

Run against the CSR address-mapping snippet (`csr_address_mapping.txt`),
this prompt extracts 2-3 "parameters" out of the CSR encoding convention
table (e.g. treats "the top two bits indicate read/write vs read-only" as
if it were an implementation choice). It isn't -- it's a fixed encoding
rule. The prompt has no anchor for what actually signals optionality, so
it pattern-matches on "this text describes a technical rule" rather than
"this text describes an implementation choice."
