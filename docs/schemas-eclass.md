---
title: ECLASS Ontology Mapping
description: How ECLASS 16 XML is mapped into GAS and PartClass
---

# ECLASS Ontology Mapping

ECLASS support relies on:

- ECLASS 16 XML dictionaries under `nmis_dpp/ontology_data/eclass_16/`.
- The script `nmis_dpp/eclass_build_mapping.py`, which:
  - Parses ECLASS XML (`dictionary_assets_en`).
  - Uses keyword heuristics to group ECLASS classes into GAS `PartClass`
    domains (`Sensor`, `Actuator`, etc.).
  - Writes `eclass_part_class_mapping.yaml` at the repo root.[cite:23]

This YAML is then consumed by `nmis_dpp.mappers.ECLASSMapper` to:

- Bind `PartClass` instances to ECLASS item/class IDs.
- Provide JSON‑LD `@context` and schema metadata.
- Validate and export an ECLASS‑vocabulary DPP.

If you update your ECLASS source XML or keyword heuristics:

```bash
python -m nmis_dpp.eclass_build_mapping
