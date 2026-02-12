
### `docs/api-model.md`

```md
---
title: Models & Part Classes
description: Python dataclasses for GAS layers and parts
---

# Models & Part Classes

The core Python types live in:

- `nmis_dpp.model` – GAS layers and `DigitalProductPassport`.
- `nmis_dpp.part_class` – universal part classes with ontology bindings.[cite:22][cite:25]

Import shortcuts are exposed from `nmis_dpp/__init__.py`:

```python
from nmis_dpp import (
  IdentityLayer, StructureLayer, LifecycleLayer, RiskLayer,
  SustainabilityLayer, ProvenanceLayer, DigitalProductPassport,
  PartClass, Sensor, Actuator, EnergyStorage, PowerConversion,
  to_dict, to_json, validate_part_class,
)
```
Each layer is a `dataclass` describing a slice of the passport
(see GAS – General Architectural Schema for conceptual details).

`PartClass` supports ontology bindings:

```python
sensor = Sensor(part_id="S-1", name="Temp Sensor", type="Sensor")
sensor.bind_ontology(
    "ECLASS",
    class_ids=[],
    case_item_ids=["0173-1#01-ABP879#017"],
    metadata={"version": "16.0"},
)
```
