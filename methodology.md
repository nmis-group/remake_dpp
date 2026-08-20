# Methodology Section — GAS Paper (Procedia Computer Science)

> **Usage:** This document is the source material for `\section{Methodology}` in `main.tex`.
> Each `###` subsection maps to a `\subsection{}`. The section is written in academic prose
> ready for direct adaptation. Target length in the final paper: ~600–900 words of body text.
> This section sits *after* Architecture — it explains **how** the system was built, not what it does.

---

## 4. Methodology

The development of GAS followed a Design Science Research (DSR) methodology, in which the primary research output is a functional software artefact — the `nmis_dpp` package — whose design decisions are grounded in systematic analysis of the problem domain and evaluated against concrete requirements. DSR is appropriate here because the contribution is an architectural pattern and its implementation rather than a theoretical proposition, and because validity is demonstrated through the artefact's ability to solve the identified interoperability problem across multiple real-world ontologies. The development proceeded through five sequential phases: problem formalisation, ontology analysis, canonical model derivation, pattern selection and implementation, and validation.

---

### 4.1 Problem Formalisation

The research began by characterising the interoperability gap through a structured survey of the industrial DPP ecosystem. Existing solutions — including the Asset Administration Shell (AAS/BaSyx), Catena-X, CIRPASS-2, and commercial DPP-as-a-Service platforms — were evaluated against five criteria: (i) support for multi-ontology ingestion, (ii) presence of a schema-agnostic intermediate representation, (iii) support for ISA-95/B2MML, (iv) SME accessibility (open-source, pip-installable), and (v) compliance with EU regulatory output formats. None of the surveyed solutions satisfied all five criteria simultaneously, confirming the requirement for a new artefact. The gap was formally defined as the absence of a reusable ETL and harmonisation layer capable of ingesting heterogeneous industrial data and emitting validated, regulation-compliant DPP outputs.

From this gap analysis, three primary design requirements were derived:

- **R1 (Schema-agnosticism):** The internal representation must be independent of any single ontology vocabulary so that adding a new input or output schema does not require changes to the canonical model.
- **R2 (Domain completeness):** The part classification taxonomy must cover the principal engineering domains represented in both ECLASS 16 and ISA-95/B2MML without privileging either ontology's terminology.
- **R3 (Regulatory compliance):** Output mappers must be capable of generating exports that satisfy the mandatory field requirements of the EU Battery Passport (Regulation 2023/1542) and the broader ESPR framework.

---

### 4.2 Ontology Analysis and Cross-Schema Pattern Extraction

To satisfy R1 and R2, a systematic analysis of the two primary industrial ontologies was conducted: ECLASS 16 (XML dictionary export, `urn:eclass:xml-schema:dictionary:5.0`) and ISA-95/B2MML V0600 (XSD schema suite covering Equipment, Material, Process Segment, Production Capability, and Production Performance).

For each ontology, all class definitions and their associated natural-language descriptions were extracted programmatically. In the case of ECLASS 16, the XML parser traversed the dictionary hierarchy, extracting `class` elements and their `preferred_name` and `definition` strings. For ISA-95, the XSD parser resolved `$ref` chains across the full AllSchemas document, extracting `complexType` and `element` definitions with their `annotation/documentation` text.

A keyword-heuristic domain-scoring algorithm was then applied to every extracted definition. For each of the fifteen candidate part-class domains (e.g., PowerConversion, EnergyStorage, Sensor), a curated lexicon of domain-specific multi-word phrases was defined. Each class definition was scored against all fifteen domain lexica by counting phrase occurrences, with multi-word phrases assigned higher weight than single-word matches to reduce false positives (e.g., the generic term "power" is not a trigger, but "power supply" and "ac/dc converter" are). A minimum score threshold of two hits was required before a class was assigned to any domain, and each class was assigned to the single highest-scoring domain to enforce mutual exclusivity. Classes that scored below the threshold in all domains were discarded as insufficiently specific.

The output of this phase was a YAML mapping file (`eclass_part_class_mapping.yaml`) that listed, for each of the fifteen domains, the ECLASS class identifiers (IRDIs) and case-item identifiers that fell within it, and an equivalent mapping for ISA-95 equipment class identifiers. The overlap between the two mappings confirmed that the fifteen-domain taxonomy was sufficiently comprehensive to represent the engineering vocabulary of both standards without ontology-specific residual classes. This cross-ontology alignment process directly produced the `OntologyBinding` data structure: a generic container that stores ontology-specific class identifiers against a domain-neutral label, enabling a single `PartClass` instance to carry bindings from multiple ontologies simultaneously.

---

### 4.3 Canonical Layer Derivation

The six-layer GAS model was derived by mapping the identified DPP regulatory requirements (EU Regulation 2023/1542, ESPR, and the ARTISAN B2MML interoperability report for ISA-95/ERP-MES integration) against the data domains covered by the extracted ontology mappings. Each regulatory or interoperability requirement was assigned to the most semantically appropriate layer:

- Identity and certification requirements (GTIN, conformity, ownership) → **IdentityLayer**
- Physical composition and BoM requirements → **StructureLayer** (host of `PartClass` instances)
- Manufacturing traceability and end-of-life requirements → **LifecycleLayer**
- Hazardous substance declarations, FMEA, and SBOM requirements → **RiskLayer**
- Carbon footprint, recycled content, and repairability requirements → **SustainabilityLayer**
- Audit trail, digital signatures, and EPCIS traceability requirements → **ProvenanceLayer**

The six layers were chosen to achieve orthogonality: each layer covers a distinct concern with no mandatory cross-layer dependencies, allowing mappers to implement only the layers relevant to their target schema. Python `dataclasses` were selected for the layer implementation because they provide zero-overhead serialisation via `dataclasses.asdict()`, enforce field typing at static analysis time, and impose no framework dependency on consumers.

---

### 4.4 Design Pattern Selection and Implementation

Two established software engineering patterns were applied to implement the schema-agnosticism requirement (R1).

The **Strategy pattern** was applied to the output layer. An abstract base class `SchemaMapper` defines the mapping interface (six `map_<layer>()` methods plus `validate_mapping()`), and each concrete mapper (`BatteryDPPMapper`, `ECLASSMapper`, `ISA95Mapper`) implements this interface independently. The `SchemaRegistry` singleton acts as the context object, holding a dictionary of mapper classes keyed by schema name and dispatching to the appropriate strategy at runtime. Lazy registration (`register_lazy()`) defers mapper class import until first use, keeping package startup time independent of the number of registered schemas.

The **Adapter pattern** was applied to the input layer. Each input adapter (`build_dpp_from_eclass`, `build_dpp_from_isa95`, `build_dpp_from_csv`) presents the same function signature — accepting source file paths and an optional configuration dictionary — and returns a `DigitalProductPassport`. This uniform interface allows the public `create_dpp()` orchestrator to dispatch to any adapter without conditional branching on the input schema type beyond a single lookup in the `_INPUT_ADAPTER_MAP` dispatch table.

The CSV adapter additionally accepts a declarative `mapping.yml` configuration file, enabling end-users to map arbitrary column headers to GAS layer fields without writing Python code. This design decision was driven by the finding that a large proportion of SME product data resides in spreadsheet exports, and that requiring code-level modification to ingest such data would constitute a significant adoption barrier.

---

### 4.5 Validation

The framework was validated at two levels.

**Unit and integration testing** was implemented using `pytest`. The test suite covers: individual `PartClass` subclass instantiation and serialisation (`test_part_class.py`); all six layer-mapping methods of each mapper with both empty and fully-populated inputs (`test_mappers.py`, `test_battery_dpp_mapper.py`); `SchemaRegistry` registration, alias resolution, lazy loading, and error propagation (`test_schema_registry.py`, `test_registry_extended.py`); and the complete `DigitalProductPassport` model (`test_model.py`). Mapper-level validation tests verify that `validate_mapping()` raises on missing mandatory fields (e.g., missing `manufacturer` and `carbonFootprint` in the Battery DPP mapper) and passes for fully compliant documents.

**Proof-of-concept integration** was demonstrated through a coffee machine product example distributed with the package. The example constructs a `DigitalProductPassport` containing representative parts from multiple `PartClass` subclasses (including `Thermal`, `Fluidics`, `ControlUnit`, and `Connectivity` instances), passes it through each of the three output mappers, and verifies that the resulting JSON-LD documents are structurally valid and carry the expected ontology bindings. This end-to-end demonstration confirms that the three-tier pipeline — adapter, canonical model, mapper — operates correctly in a realistic multi-part product scenario.

---

## Notes for LaTeX Conversion

- Each `###` subsection → `\subsection{}` in LaTeX.
- The three design requirements R1–R3 in Section 4.1 can be typeset as a `\begin{enumerate}` or as inline bold labels.
- The phase sequence (4.1–4.5) can be summarised in a small `\begin{figure}` flowchart if a second figure slot is available (flowchart: Problem Formalisation → Ontology Analysis → Layer Derivation → Implementation → Validation).
- If the paper is tight on space, Section 4.2 (Ontology Analysis) is the most cuttable — reduce to 2 sentences naming the approach and its output.
- The five DSR criteria table in 4.1 can be typeset as a `\begin{table}` comparing existing solutions — this may be more appropriate in Literature Review if that section is developed.
- The two design patterns (Strategy + Adapter) in 4.4 can each be reduced to one sentence if space demands it.
