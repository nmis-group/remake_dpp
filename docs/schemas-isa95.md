
### `docs/schemas-isa95.md`

```md
---
title: ISA‑95 / B2MML Mapping
description: How ISA‑95 equipment and material concepts map into GAS
---

# ISA‑95 / B2MML Mapping

ISA‑95 integration uses the MESA B2MML / BatchML schemas in
`nmis_dpp/ontology_data/isa95/Schema/`.[cite:57]

The script `nmis_dpp/isa95_build_mapping.py`:

- Scans all `.xsd` files in the Schema directory.
- Extracts element and complexType names plus `documentation` text.
- Applies keyword heuristics to assign each definition to a GAS
  `PartClass` domain, writing `isa95_part_class_mapping.yaml`.

`nmis_dpp.mappers.ISA95Mapper` uses this mapping to:

- Attach ISA‑95 equipment/material concepts to `PartClass` instances.
- Produce ISA‑95‑like views (e.g. work definitions, capabilities)
  from a GAS `DigitalProductPassport`.

Regenerate mappings after updating XSDs or heuristics:

```bash
python -m nmis_dpp.isa95_build_mapping
