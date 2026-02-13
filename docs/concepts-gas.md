---
title: GAS – General Architectural Schema
description: Internal canonical model for Digital Product Passports
---

# GAS – General Architectural Schema

GAS is the internal, hidden canonical model that all input schemas
(ECLASS 16, ISA‑95, CSV/JSON) are mapped into before export.[cite:20]

It is implemented by:

- `nmis_dpp.model`: layer dataclasses (`IdentityLayer`, `StructureLayer`,
  `LifecycleLayer`, `RiskLayer`, `SustainabilityLayer`, `ProvenanceLayer`,
  `DigitalProductPassport`).
- `nmis_dpp.part_class`: domain‑neutral `PartClass` subclasses
  (`Sensor`, `Actuator`, `EnergyStorage`, `PowerConversion`, etc.).[cite:22][cite:25]

GAS layers:

1. **Identity layer** – global IDs, make/model, ownership, conformity.
2. **Structure layer** – hierarchy, part classes, interfaces, materials, BOM refs.
3. **Lifecycle layer** – manufacture, use, serviceability, events, end‑of‑life.
4. **Risk layer** – criticality, FMEA, security.
5. **Sustainability layer** – mass/energy, recycled content, remanufacture.
6. **Provenance layer** – signatures, trace links.[cite:20]

Users normally don’t construct all of this by hand—instead:

- Ontology adapters (ECLASS, ISA‑95) build GAS instances from source data.
- Schema mappers turn a GAS `DigitalProductPassport` into DPP JSON‑LD or other schemas.

See **Models & Part Classes** for the Python types.
