---
title: Python Usage Examples
description: End-to-end mapping flows using nmis_dpp
---

# Python Usage Examples

This page collects higher‑level examples combining:

- Ontology mapping (ECLASS / ISA‑95)
- GAS model construction
- Schema registry and mappers
- End‑to‑end DPP export

## Example: ECLASS-based Generic DPP

```python
from pathlib import Path
from nmis_dpp import (
    IdentityLayer, StructureLayer, LifecycleLayer,
    RiskLayer, SustainabilityLayer, ProvenanceLayer,
    DigitalProductPassport, Sensor,
)
from nmis_dpp.schema_registry import get_global_registry, register_default_mappers

# 1. Prepare GAS layers (in practice, built from ECLASS input)
sensor = Sensor(part_id="S-1", name="Temp Sensor", type="Sensor")

dpp = DigitalProductPassport(
    identity=IdentityLayer(
        global_ids={"uuid": "123e4567-e89b-12d3-a456-426614174000"},
        make_model={"brand": "Acme", "model": "TS-100"},
        ownership={"manufacturer": "Acme", "current_owner": "Factory A"},
        conformity=["CE"],
    ),
    structure=StructureLayer(
        hierarchy={"product": ["S-1"]},
        parts=[sensor],
        interfaces=[],
        materials=[],
        bom_refs=[],
    ),
    lifecycle=LifecycleLayer(
        manufacture={"factory": "Plant 1"},
        use={},
        serviceability={},
        events=[],
        end_of_life={},
    ),
    risk=RiskLayer(criticality={}, fmea=[], security={}),
    sustainability=SustainabilityLayer(
        mass=0.05,
        energy={},
        recycled_content={},
        remanufacture={},
    ),
    provenance=ProvenanceLayer(signatures=[], trace_links=[]),
)

# 2. Map to ECLASS schema
register_default_mappers()
registry = get_global_registry()

mapped = registry.map_dpp("ECLASS", dpp)
print(mapped["@context"])
```
See tests in `tests/test_mappers.py` and `tests/test_registry_extended.py`
for more patterns.