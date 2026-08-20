# Architecture Section — GAS Paper (Procedia Computer Science)

> **Usage:** This document is the source material for `\section{Architecture}` in `main.tex`.
> Each subsection maps directly to a LaTeX `\subsection{}`. Figures and table descriptions
> are included as prose placeholders — replace with actual TikZ/figures in the final draft.

---

## 3. Architecture

The General Architecture Subsystem (GAS) is implemented as an open-source Python package (`nmis_dpp`) whose design separates three orthogonal concerns: *data ingestion* (input adapters), *canonical representation* (the GAS model), and *schema export* (mappers and registry). This separation enables any supported source ontology to be transformed into any registered output schema through a single, schema-agnostic intermediate representation, without coupling parsing logic to export logic. The overall pipeline is illustrated conceptually as:

```
[Input Sources]  →  [Input Adapters]  →  [GAS Model]  →  [Schema Registry]  →  [Output Schema]
  ECLASS XML           eclass adapter       DigitalProductPassport    BatteryDPP / ECLASS / ISA-95
  ISA-95 XSD           isa95 adapter        (6 layers + PartClasses)
  CSV + YAML           csv adapter
```

The public entry point, `create_dpp()`, encapsulates the full pipeline in a single callable that accepts an input schema name, output schema name, source file paths, and an optional configuration directory, returning a JSON-LD–ready dictionary.

---

### 3.1 The Six-Layer GAS Data Model

The canonical representation of a Digital Product Passport within GAS is the `DigitalProductPassport` dataclass, which aggregates six independent, strongly-typed layers. Each layer is itself a dataclass, making the model serialisable without any custom marshalling logic. The six layers and their responsibilities are as follows.

**IdentityLayer** captures the globally unique identifiers of the product instance: `global_ids` (GTIN, SGTIN, serial number, manufacturer part number, UUID), `make_model` (brand, model, hardware and firmware revision), `ownership` (manufacturer, current owner, operator, and location), and `conformity` (a list of regulatory approvals such as CE, UKCA, RoHS, and FAA certifications). This layer provides the minimum information required to unambiguously locate and identify a product across supply chain boundaries.

**StructureLayer** encodes the physical and logical decomposition of the product. It holds a `hierarchy` dictionary that models the canonical industrial hierarchy (Product → Subsystem → Assembly → Component → Material), a `parts` list of typed `PartClass` instances (see Section 3.2), `interfaces` (electrical, mechanical, fluid, and data connection specifications), `materials` (composition data including CAS numbers, percentage mass, and recyclability flags), and `bom_refs` (Bill of Materials references and supersession chains). This layer is the structural backbone of the GAS model and the primary attachment point for the part classification framework.

**LifecycleLayer** tracks time-varying product state across three phases: `manufacture` (lot, batch, factory, production date, process parameters, and CO₂ equivalent at manufacture), `use` (operational counters such as hours and cycles, operating ranges, and telemetry summaries), and `serviceability` (maintenance schedule, repair procedure steps, spare part mapping, and a repairability score). It also carries a structured `events` list for major lifecycle events (installation, removal, inspection, failures, and software updates) and an `end_of_life` dictionary for disassembly instructions, hazard declarations, and recovery routing.

**RiskLayer** consolidates all risk and reliability information relevant to product safety assessment. `criticality` encodes the safety and mission classification, life-limited part (LLP) flag, and Mean Time Between Failures (MTBF). `fmea` holds a list of Failure Mode, Effects, and Criticality Analysis entries (failure mode, effect, mitigation, and hazardous substance declarations). `security` carries the Software Bill of Materials (SBOM), known vulnerability data, cryptographic signing key reference, and firmware update policy. This layer directly supports compliance with EU product safety and cybersecurity regulations.

**SustainabilityLayer** captures the environmental footprint and circular economy eligibility of the product: `mass` (total mass breakdown), `energy` (standby and active power consumption, and water use), `recycled_content` (percentage post-consumer recycled content, bio-based fraction, and restricted substances), and `remanufacture` (remanufacturability eligibility flag and grading criteria). This layer maps naturally to the mandatory fields of the EU Battery Passport under Regulation 2023/1542 and the broader Eco-design for Sustainable Products Regulation (ESPR).

**ProvenanceLayer** records trust and traceability metadata: `signatures` (a list of manufacturer and service authority certificates, such as EASA Form 1 and manufacturer declarations, stored as structured dicts), and `trace_links` (EPCIS event URIs, QR/NFC tag identifiers, and blockchain anchors). This layer enables downstream verification of data provenance without prescribing a specific distributed ledger or traceability technology.

---

### 3.2 Domain-Neutral Part Classification Framework

The `PartClass` base class and its fifteen typed subclasses form the ontology-agnostic vocabulary through which GAS describes physical components across manufacturing domains. The design principle is that a part carries its engineering semantics (strongly-typed attributes meaningful to an engineer) independently of any particular ontology's vocabulary.

**Base class — `PartClass`:** Every part instance holds a `part_id` (unique within the DPP), a `name`, a `type` label, a flexible `properties` dictionary for attributes not covered by the typed subclass fields, and an `ontology_bindings` dictionary that maps ontology names (e.g., `"ECLASS"`, `"ISA-95"`) to `OntologyBinding` objects.

**`OntologyBinding`** is the key abstraction enabling multi-ontology compatibility. Each binding carries: `ontology_name` (human-readable identifier), `class_ids` (a list of ontology class identifiers, e.g., ECLASS IRDIs or ISA-95 equipment class codes), `case_item_ids` (identifiers for instance-level or "case-of" items within the ontology), and a free-form `metadata` dictionary for per-property IRDIs, unit mappings, language labels, and hierarchy relationships. A single `PartClass` instance can therefore be simultaneously bound to ECLASS 16, ISA-95, and any custom schema without modifying its core engineering attributes.

**The fifteen typed subclasses** cover the principal engineering domains encountered in industrial products:

| Subclass | Domain | Key Typed Attributes |
|---|---|---|
| `PowerConversion` | PSUs, inverters, alternators | `input_voltage`, `output_voltage`, `power_rating`, `efficiency` |
| `EnergyStorage` | Batteries, capacitors | `capacity`, `chemistry`, `recharge_cycles`, `nominal_voltage` |
| `Actuator` | Motors, valves, servos | `torque`, `speed`, `duty_cycle`, `actuation_type` |
| `Sensor` | Temperature, pressure, IMU | `sensor_type`, `range`, `accuracy`, `response_time` |
| `ControlUnit` | ECU, MCU, PLC, FADEC | `cpu_type`, `memory`, `firmware`, `io_count` |
| `UserInterface` | HMI, touchscreens, indicators | `ui_type`, `display_size`, `input_methods` |
| `Thermal` | Heaters, fans, heat exchangers | `power`, `delta_t`, `airflow` |
| `Fluidics` | Pumps, tanks, lines, filters | `flow_rate`, `pressure`, `fluid_type`, `volume` |
| `Structural` | Frames, housings, blades | `material`, `mass`, `dimensions`, `load_rating` |
| `Transmission` | Gears, bearings, belts, shafts | `torque_rating`, `speed_rating`, `transmission_type` |
| `Protection` | Fuses, breakers, EMI filters | `protection_type`, `rating`, `response_time` |
| `Connectivity` | Connectors, harnesses, buses | `interface_type`, `connector_standard`, `pin_count` |
| `SoftwareModule` | Firmware, control laws, DSP | `version`, `language`, `license`, `checksums` |
| `Consumable` | Filters, seals, oils | `consumable_type`, `capacity`, `replacement_interval` |
| `Fastener` | Screws, rivets, adhesives | `fastener_type`, `material`, `diameter`, `strength` |

This taxonomy was derived by analysing the structural content of both the ECLASS 16 ontology and the ISA-95/B2MML XSD schemas, extracting recurring equipment classification hierarchies using keyword-heuristic domain scoring scripts (`eclass_build_mapping.py`, `isa95_build_mapping.py`), and consolidating them into fifteen domain-neutral categories that subsume the most frequently referenced equipment classes across both standards.

---

### 3.3 Schema Registry and Mapper Pattern

The Schema Registry implements a Strategy pattern: a central dispatcher that decouples the GAS model from any specific output format. This allows new output schemas to be registered without modifying existing code.

**`SchemaMapper` (abstract base class)** defines the interface that every output mapper must implement: `get_schema_name()`, `get_schema_version()`, `get_context()` (returns the JSON-LD `@context` block), and six layer-mapping methods — `map_identity_layer()`, `map_structure_layer()`, `map_lifecycle_layer()`, `map_risk_layer()`, `map_sustainability_layer()`, and `map_provenance_layer()` — plus `validate_mapping()` for post-hoc compliance checking against mandatory fields.

**Concrete mappers** implement these methods for each target schema:

- **`BatteryDPPMapper`** targets EU Regulation 2023/1542 (Annex XIII). It emits a JSON-LD document with the EU Battery Passport `@context`, mapping `IdentityLayer` to product identification and manufacturer fields, `LifecycleLayer` to manufacturing date and state-of-health fields, `SustainabilityLayer` to carbon footprint, recycled content, and renewable material fields, and `RiskLayer` to hazardous substance declarations. `validate_mapping()` enforces the mandatory fields specified by the regulation.

- **`ECLASSMapper`** targets ECLASS 16.0. It produces a JSON-LD document with the ECLASS `@context` covering core ECLASS properties, part class type codes (ETIM), units (UN/ECE), and manufacturer-specific extension fields. Each `PartClass` in `StructureLayer.parts` is serialised with its ECLASS IRDI bindings from the `OntologyBinding.class_ids` field.

- **`ISA95Mapper`** targets ISA-95/IEC 62264 and its XML-based serialisation format B2MML V0600. It produces a JSON-LD document with the B2MML `@context` covering Equipment, Material, Process Segment, and Work Order vocabulary. `IdentityLayer` maps to ISA-95 Equipment identity fields; `LifecycleLayer` maps to Work Order and Production Performance structures.

**`SchemaRegistry`** is a singleton (accessed via `get_global_registry()`) that maintains a dictionary from schema name (and aliases) to mapper classes. Mappers can be registered eagerly (`register()`) or lazily (`register_lazy()`, importing the mapper class only on first use). A YAML catalog (`config/schemas.yml`) provides an optional declarative registration mechanism. The registry exposes `map_dpp(schema, dpp)` as the primary dispatch method, which instantiates the appropriate mapper and calls all six layer-mapping methods in sequence.

---

### 3.4 Input Adapters

Three input adapters convert heterogeneous source formats into `DigitalProductPassport` instances, each implementing an ETL-like extraction and transformation pipeline.

**ECLASS adapter (`build_dpp_from_eclass`)** parses ECLASS 16 XML export files, extracts class hierarchies, IRDI property codes, and associated values, and maps them to GAS layers. A domain classification step (`eclass_build_mapping.py`) scores each extracted element against keyword heuristics to assign it to one of the fifteen `PartClass` subclasses and constructs `OntologyBinding` entries carrying the original ECLASS class IDs and case item IDs.

**ISA-95 adapter (`build_dpp_from_isa95`)** parses B2MML XSD schema files and instance documents from the ISA-95/IEC 62264 standard. The adapter resolves `$ref` chains within the AllSchemas XSD, extracts equipment and material definitions, and maps them to GAS structure and lifecycle layers. A parallel domain mapping script (`isa95_build_mapping.py`) applies the same keyword-heuristic classification to assign ISA-95 equipment class definitions to `PartClass` subclasses with `OntologyBinding` entries carrying ISA-95 equipment class identifiers.

**CSV adapter (`build_dpp_from_csv`)** accepts flat tabular data together with a user-supplied `mapping.yml` configuration file that specifies column-to-field mappings for each GAS layer and part class attribute. This adapter enables rapid integration of legacy spreadsheet data and ERP exports without requiring any ontology-specific knowledge from the operator.

---

### 3.5 Public API and End-to-End Pipeline

The package exposes a single public function, `create_dpp()`, that composes the adapters and registry into a complete ETL pipeline:

```python
result = create_dpp(
    input_schema  = "ECLASS",          # or "ISA-95", "CSV"
    output_schema = "BatteryDPP",      # or "ECLASS", "ISA-95"
    files         = [Path("asset.xml")],
    config_dir    = Path("config/"),
)
```

Execution proceeds in three steps: (1) the input adapter is resolved from `input_schema` and called with the provided files and optional YAML configuration to produce a `DigitalProductPassport`; (2) the global `SchemaRegistry` is queried for the mapper corresponding to `output_schema`; (3) the mapper's six layer-mapping methods are called in sequence and their results are assembled into a JSON-LD–ready dictionary that is returned to the caller. A command-line interface (`cli.py`) wraps this function for direct terminal invocation.

The three-layer separation — adapter, GAS model, mapper — ensures that adding a new input source requires only writing a new adapter function, adding a new output schema requires only implementing the `SchemaMapper` interface, and neither change requires modifying the canonical GAS model or any other existing component. This design directly addresses the interoperability gap identified in Section 1 by providing a replicable, extensible architectural pattern that can bridge any two ontologies for which adapters and mappers exist.

---

## Notes for LaTeX Conversion

- Replace the ASCII pipeline diagram with a TikZ `\tikzpicture` or a figure showing the three-tier architecture.
- Replace the Markdown table in Section 3.2 with a `\begin{table}` / `\tabular` environment with a `\caption{}`.
- Each `###` subsection maps to `\subsection{}` in the paper.
- The code snippet in Section 3.5 can use `\begin{lstlisting}[language=Python]` or be removed if space is tight.
- Target length for the Architecture section in a Procedia 8-page paper: approximately 800–1,200 words of body text plus one figure and one table.
