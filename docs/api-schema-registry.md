
### `docs/api-schema-registry.md`

```md
---
title: Schema Registry & Mappers
description: Registering and using schema mappers to export DPPs
---

# Schema Registry & Mappers

`nmis_dpp.schema_registry.SchemaRegistry` is the central place to:

- Register schema mappers (ECLASS, ISA‑95, etc.).
- Look up mappers by canonical name or alias.
- Map a full `DigitalProductPassport` or just individual layers.[cite:24]

Basic usage:

```python
from nmis_dpp.schema_registry import get_global_registry, register_default_mappers

register_default_mappers()
registry = get_global_registry()

# List available schemas (e.g. ["ECLASS", "ISA-95"])
print(registry.list_schemas())

info = registry.info("ECLASS")
print(info["name"], info["version"])
```

Mappers live in `nmis_dpp/mappers/` and subclass `SchemaMapper`
from `nmis_dpp.schema_base`:

- `ECLASSMapper` – exports ECLASS‑vocabulary DPP JSON‑LD.
- `ISA95Mapper` – exports ISA‑95/B2MML‑compatible views.

Each mapper implements:

- `map_dpp(dpp)` – full passport → schema dict.
- Layer methods (`map_identity_layer`, `map_structure_layer`, …).
- `validate_mapping(mapped)` – schema‑specific validation.
- `get_context()` – JSON‑LD @context.