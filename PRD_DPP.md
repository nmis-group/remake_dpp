# DPP Bridge / ReMake DPP: Product Requirements Document (Updated with GAS)

### TL;DR

Manufacturing and other product companies (machinery, textiles, batteries, etc.) struggle to implement Digital Product Passports (DPPs) due to fragmented data, complex standards, and lack of integration tools. ReMake DPP / **DPP Bridge** is an open source Python package that enables developers to map business data to DPP standards using automated configuration tools, with an internal **General Architectural Schema (GAS)** that normalises product data across domains and schemas before export.

**DPP Bridge** provides the **missing ETL and harmonisation layer** for the Digital Product Passport ecosystem: it ingests enterprise product/manufacturing data in multiple schemas (e.g. ISA‑95, ECLASS 16) and arbitrary ontologies, converts them into GAS, and then exports EU‑compliant DPPs or other schema representations (e.g. ECLASS 16, ISA‑95) using **JSON‑LD as the primary output format**.

Unlike heavyweight industrial solutions or expensive SaaS platforms, DPP Bridge is:  
- **SME-accessible**: Install with pip, generate DPP in a few lines of code.
- **Standards-based**: Leverages proven libraries (e.g. Pydantic, Bonobo ETL, PyLD) and standard ontologies.
- **Schema-agnostic**: Uses GAS as a hidden intermediate layer, enabling mapping from any supported ontology to any target DPP schema.  
- **Manufacturing-native**: Built‑in ISA‑95 B2MML connector and ECLASS16 support (unique in market).
- **Bidirectional**: Can generate ISA‑95 work orders or other operational artefacts from DPPs (circular economy).

**Tagline:** *“The ETL and harmonisation layer the DPP ecosystem is missing – transform heterogeneous product data into EU‑compliant passports in minutes, not months.”*

***

## Problem Statement

### The Compliance Deadline

Manufacturing and product companies face mandatory Digital Product Passport regulations across multiple sectors:
- **Battery Passport:** February 2027.
- **Textile DPP:** 2027–2028.
- **ESPR Generic DPP:** Rolling out 2027–2030.

These regulations will expand to additional product groups, increasing the need for cross‑domain, schema‑independent tooling.

### The Current Gap

Existing data lives in many systems and schemas:

```
┌─────────────────┐                              ┌─────────────┐
│  Your Data      │          ?????????           │  EU DPP     │
│  ─────────────  │                              │  Registry   │
│  • MES (ISA-95) │  ──────── MISSING ────────►  │             │
│  • PLM / ERP    │          TOOLING             │  QR Code    │
│  • ECLASS 16    │                              │  Consumer   │
│  • Textiles DB  │                              │  OEM/Buyer  │
└─────────────────┘                              └─────────────┘
```

There is no general solution that:  
- Ingests arbitrary domain data (machinery, textiles, batteries, etc.) in differing schemas/ontologies.  
- Normalises it into a reusable product model.  
- Then outputs into multiple DPP or domain schemas on demand.

### Why Existing Solutions Fall Short

| Solution | Problem |
|----------|---------|
| **BaSyx/AAS Ecosystem** | Defines data model, not transformation. Requires deep expertise. No ISA‑95 or multi‑schema ETL. |
| **Catena‑X** | Automotive only, tied to specific ecosystem. Requires certification, infrastructure, membership (€€€). |
| **CIRPASS‑2** | Defines requirements, not implementations. No reusable code. |
| **Commercial DPP‑as‑a‑Service** | €10–50K/year, vendor lock‑in, limited schema control. Overkill for SMEs. |
| **Manual Excel/CSV** | Slow, error‑prone, does not scale, no validation, no ontology management. |

### The Real Gap: No “ETL + GAS for DPP”

> *“The asset administration shell is not yet ready for the market, which makes widespread implementation difficult.”* — Industry expert, March 2025[1]

**Nobody provides tools to get multi‑schema data INTO a general product representation and back OUT into DPP formats and other schemas.**[1]

DPP Bridge introduces **GAS** as a hidden internal canonical model so that data from any supported ontology can be transformed into any target DPP or domain schema.

***

## Goals

### Business Goals (6–12 Months)

| Goal | Metric | Target | Why It Matters |
|------|--------|--------|----------------|
| **Adoption** | PyPI downloads | 100+ | Validates market need.  |
| **Community** | GitHub stars | 20+ | Developer interest signal.  |
| **Validation** | Pilot implementations | 2+ companies | Real‑world testing.  |
| **Ecosystem** | Listed by CIRPASS/IDTA | Yes | Legitimacy in DPP space.  |
| **ISA‑95 Adoption** | Companies using B2MML connector | 1 | Validates differentiator.  |
| **Multi‑schema Usage** | Production use of GAS with at least 2 ontologies (ISA‑95, ECLASS16) | 1 pilot | Demonstrates ontology‑agnostic approach. |

### User Goals

- Enable users to find and use compliant DPPs from their own business data with tooling to support mapping across schemas via a hidden GAS layer.
- Provide intuitive tools (Python package) for configuring and validating DPP/GAS data models, including ontology registration and mapping.
- Ensure DPPs are interoperable, meet regulatory requirements, and can be re‑expressed in multiple domain schemas (e.g. input ISA‑95, output ECLASS16).
- Offer starter kits, templates, and example GAS mappings to accelerate onboarding and reduce learning curve.

### Non‑Goals

- No direct connectors to ERP/PLM or other business systems in the initial release.
- No real‑time or cloud‑based validation; only offline, local validation is supported.
- No support for proprietary or non‑standard DPP formats outside the targeted standard(s) in MVP.
- No user‑facing editing or visualisation of GAS itself in MVP (GAS remains an internal model).

***

## User Stories

### Primary Personas

#### Data‑Responsible Operations Manager at an SME

This persona is not a DPP expert, and also not an ontology expert. Their job is to keep production running and address new compliance risks as they arise, across different product lines (e.g. machinery and textile components). They rarely know about “DPP schemas” or “ECLASS vs ISA‑95” in detail and need simple pathways from existing files to compliant, exportable DPPs.[1]

**User Attributes:**  
- Often responsible for compliance or digital innovation, but not a standards specialist.
- Has limited technical support; may rely on spreadsheets or ad‑hoc database exports.
- Measures success by successfully submitting compliance files with minimal disruption.
- Unsure which DPP models are official, required, or suitable for their products.

**User Stories:**  
- As a Data‑Responsible Manager, I want to see a list of available DPP schemas by sector so I can understand which ones apply to our products.
- As a new DPP user, I want clear badges showing which DPP schemas are “EU‑verified” or “industry‑accepted,” so I do not implement a dead‑end standard.
- As an operations lead, I want to upload my company’s exports and get a simple gap report, identifying what data I have, what is missing, and what is required by the selected DPP schema.
- As a non‑expert in digital standards, I want step‑by‑step guidance to help me turn my existing data into a compliant DPP, so I can avoid costly mistakes or penalties.
- As a business owner, I want recommendations for filling critical data gaps (e.g. “ask your supplier for X,” or “track Y in future exports”), reducing time‑to‑compliance.

### New/Extended User Stories (GAS and Multi‑schema)

- As a data engineer, I want to ingest product data in different schemas (ISA‑95 for manufacturing events, ECLASS16 for parts, custom JSON for textiles) and have the package normalise them into a common hidden model, so I do not have to maintain N×M direct mappings.  
- As a DPP integrator, I want to convert existing ECLASS16‑based product records into an internal GAS representation and then export an EU DPP JSON‑LD plus an ISA‑95 compatible view for MES integration.  
- As a researcher, I want to define a new ontology adapter that maps my experimental product schema into GAS without modifying core DPP logic, so I can test new DPP concepts.  

### Secondary Personas

**Standards Organization Representative**  
- As a standards organization member, I want to review and contribute to the open source implementation, so that it aligns with evolving DPP requirements and emerging ontologies.

**Consultant**  
- As a consultant, I want to use the package as a reference for client implementations, so that I can accelerate DPP adoption across multiple sectors using one canonical model.

**Researcher**  
- As a researcher, I want to extend the framework for new DPP standards, so that I can prototype and test emerging requirements without re‑implementing ETL.

***

## Architecture

### High‑level Architecture (with GAS)

```
┌─────────────────────────────────────────────────────────────────────┐
│                           DPP BRIDGE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  CONNECTORS          ONTOLOGY/GAS LAYER          EXPORTS            │
│  ──────────          ─────────────────           ───────            │
│                                                                     │
│  ┌─────────┐         ┌──────────────────┐       ┌─────────────┐    │
│  │ ISA-95  │         │   GAS Models     │       │  JSON-LD    │    │
│  │ B2MML   │───┐     │ (model.py,      │   ┌───►│  DPP(s)     │    │
│  └─────────┘   │     │  part_class.py) │   │    └─────────────┘    │
│                │     └──────────────────┘   │                      │
│  ┌─────────┐   │     ┌──────────────────┐   │    ┌─────────────┐   │
│  │ ECLASS  │───┼───► │  Schema Registry │ ──┼───►│ ECLASS 16   │   │
│  │ 16 XML  │   │     │  & Mappings      │   │    └─────────────┘   │
│  └─────────┘   │     └──────────────────┘   │                      │
│                │                             │    ┌─────────────┐   │
│  ┌─────────┐   │                             └───►│ ISA-95 /    │   │
│  │ Data in │───┘                                  │ other views │   │
│  │ JSON    │                                      └─────────────┘   │
│  └─────────┘                                                        │
│                                                                     │
│  Future - REVERSE FLOW (Circular Economy)                           │
│  ───────────────────────────────                                     │
│  Battery DPP ──► GAS ──► ISA-95 Work Definition ──► MES (repairs)   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

The **General Architectural Schema (GAS)** sits at the heart of the system, transforming heterogeneous input schemas to a unified product representation and then to required outputs.

***

## GAS: General Architectural Schema

### Concept

GAS is a **hidden canonical model** implemented in `model.py` and `part_class.py`, which:  
- Represents products in a way that spans machinery, textiles, batteries and other domains.  
- Encodes identity, structure, lifecycle, risk/criticality, sustainability, and provenance.[1]
- Provides a neutral part‑class taxonomy with typed properties, reusable across sectors.  

Users do not interact with GAS directly: they provide input data in their schema/ontology, and request an output schema (e.g. ECLASS16 DPP JSON‑LD); DPP Bridge maps input → GAS → output.

### GAS Layers (`model.py`)

`model.py` defines the following main layers:

1. **Identity layer (who/what is this thing?)**  
   - `global_ids`: GTIN/SGTIN, serial, manufacturer part number, UUID.  
   - `make_model`: brand, model, hardware revision, firmware revision.  
   - `ownership_custody`: manufacturer, current owner, operator, location.  
   - `conformity`: certifications/approvals (CE/UKCA, FAA/EASA, NSF, RoHS/REACH, etc.).  

2. **Structure layer (how is it built?)**  
   - `product_structure`: Product → Subsystem → Assembly → Component → Material hierarchy.  
   - `part_class`: domain‑agnostic classes (e.g. Sensor, Actuator, PowerConversion, EnergyStorage, SoftwareModule).  
   - `interface`: electrical (voltage, connector), fluid (ports, media), data (protocols), mechanical (mount pattern).  
   - `materials`: substance list with CAS, mass fraction (%), recyclability indicators.  
   - `bom_refs`: where this part appears, alternates, supersessions.

3. **Lifecycle layer (what has happened to it?)**  
   - `manufacture`: lot/batch, factory, date, process, CO₂e.  
   - `use`: counters (hours, cycles), parameter ranges, telemetry summaries.  
   - `serviceability`: maintenance schedule, repair steps, spare‑part mapping, repairability score.  
   - `events`: installs, removals, inspections, failures, software updates (with signatures).  
   - `end_of_life`: disassembly steps, hazards, recovery routes.

4. **Risk & criticality (how important/safe?)**  
   - `criticality`: safety/mission levels, life‑limited part (LLP) flags, MTBF.  
   - `fmea`: failure modes, effects, mitigations.  
   - `security`: SBOM, vulnerabilities, signing keys, update policy.

5. **Sustainability & circularity**  
   - `mass_energy`: mass breakdown, standby/active energy, water use.  
   - `recycled_content`: percentage post‑consumer recycled, bio‑based, restricted substances.  
   - `remanufacture`: eligibility, grading criteria, core return.

6. **Provenance & trust**  
   - `signatures`: manufacturer & service signatures, certificates (e.g. EASA Form 1).  
   - `trace_links`: EPCIS/GS1 events, QR/NFC tag bindings.

These layers are implemented with typed models (e.g. Pydantic), and used as the internal representation for all mapping and export logic.

### Part Classes (`part_class.py`)

`part_class.py` provides a **neutral and reusable** part‑class taxonomy:

- `PowerConversion` (PSUs, inverters, alternators).  
- `EnergyStorage` (batteries, capacitors).  
- `Actuator` (motors, valves, servos).  
- `Sensor` (temperature, pressure, flow, vibration, IMU).  
- `ControlUnit` (ECU, MCU boards, FADEC).  
- `UserInterface` (HMI, buttons, touchscreens, indicators).  
- `Thermal` (heaters, exchangers, fans).  
- `Fluidics` (pumps, tanks, lines, filters).  
- `Structural` (housings, frames, casings, blades, disks).  
- `Transmission` (gears, bearings, belts, shafts).  
- `Protection` (fuses, breakers, filters, EMI/RFI).  
- `Connectivity` (harnesses, connectors, buses).  
- `SoftwareModule` (firmware, control laws, DSP blocks).  
- `Consumable` (water filters, seals, oils, coffee beans).  
- `Fastener` (screws, rivets, adhesives).

Each class defines a **typed property set**, for example:  
- `Actuator`: torque, speed, duty cycle, voltage.  
- `Sensor`: range, accuracy, drift.  
- `Thermal`: power, delta‑T, airflow.  

These classes are referenced in the GAS structure layer and form a stable base for ontology mappings from ISA‑95, ECLASS16, and future schemas.

***

## Multi‑schema Conversion via GAS

### Input Ontologies and Schema Registry

The package supports multiple input ontologies and is designed to scale to more:

- **ISA‑95**: via B2MML connector and `isa_build_mapping.py` for ontology‑to‑GAS mapping.
- **ECLASS16**: via XML dictionaries under `ontology_data/eclass_16` and `eclass_build_mapping.py`.
- **Additional schemas**: can be added by registering a new schema adapter and mapping rules in `schema_registry.py` and custom build‑mapping modules.

The **schema registry**:  
- Maintains a catalogue of known schemas and ontologies (ISA‑95, ECLASS16, etc.).
- Defines mapping pipelines: Input schema → GAS → Output schema (including DPP JSON‑LD contexts).
- Ensures that the same GAS model can produce multiple downstream representations.

### Conversion Flow

1. **Input data parsing**  
   - The user provides data in any supported schema/ontology (e.g. ISA‑95 XML, ECLASS16 XML, CSV, JSON).  
   - Connectors parse these sources using the appropriate build‑mapping module.

2. **Ontology‑to‑GAS mapping**  
   - Mappings in `eclass_build_mapping.py`, `isa_build_mapping.py`, and future adapters populate `model.py` and `part_class.py` instances.  
   - GAS models now contain a fully normalised representation of the product and its lifecycle.

3. **GAS‑to‑schema conversion**  
   - The user selects a target schema (e.g. “Battery DPP JSON‑LD using ECLASS16 vocabulary” or “ISA‑95 work order”).
   - The schema registry triggers a mapping from GAS models to the target schema output, using exporters (e.g. JSON‑LD, XML).

4. **DPP Representation**  
   - The final DPP representation is generated from GAS in the target schema, ensuring consistent identity, lifecycle, and sustainability information across sectors.

### Package Layout (Updated)

```text
nmis_dpp_test/
├── nmis_dpp/
│   ├── ontology_data/
│   │   ├── eclass_16/
│   │   │   ├── dictionary_assets_en/
│   │   │   │   ├── ECLASS16_0_ASSET_EN_SG_13.xml
│   │   │   │   ├── ...
│   │   │   │   └── ECLASS16_0_ASSET_EN_SG_90.xml
│   │   │   ├── unitsml_en/
│   │   │   │   └── ECLASS16_0_UNITSML_EN.xml 
│   │   │   └── ECLASS_ASSET_XML_Read_Me_EN_v1.pdf 
│   │   ├── isa95/
│   │   │   ├── dictionary_assets_en/
│   │   │   │   └── isa95.xml
│   │   └── README.md 
│   ├── __init__.py 
│   ├── eclass_build_mapping.py      # ECLASS16 → GAS build mapping
│   ├── isa_build_mapping.py         # ISA95 → GAS build mapping 
│   ├── model.py                     # Core GAS models for DPP layers 
│   ├── part_class.py                # Universal part class set 
│   ├── schema_base.py               # Base schema abstractions for DPP/GAS layers 
│   ├── schema_registry.py           # Schema & ontology registry (GAS as hub) 
│   └── utils.py                     # Helper functions (e.g. ID generation) 
├── tests/ 
│   ├── test_model.py 
│   ├── test_part_class.py
│   ├── test_schema_registry.py 
│   └── test_schema_registry_second.py 
├── pyproject.toml  
├── LICENSE.txt 
└── README.md 
```

GAS remains **hidden from end‑users**: they only configure mappings and choose input/output schemas; the package uses GAS internally as a translation layer.

***

## Functional Requirements

### Data Mapping & Configuration (Priority: High)

- **Ontology‑aware Mapping Tool**  
  - Allow users to map their business data files (CSV, JSON, XML, ISA‑95 XML, ECLASS16 XML) to the DPP data model via GAS.
  - Provide configuration primitives to select input schema, target DPP schema, and intermediate ontology mappings.

- **Starter Kits / Templates**  
  - Provide pre‑built mapping templates for:  
    - Battery DPP (ISA‑95 → GAS → Battery DPP JSON‑LD).  
    - Textile DPP (custom CSV → GAS → Textile DPP JSON‑LD).  
    - Generic DPP (ECLASS16 → GAS → Generic DPP JSON‑LD).  

- **Configuration Interfaces**  
  - Offer both CLI and (future) web‑based configuration interfaces to manage mapping flows from input schemas to GAS and onward to output schemas.

### Validation & Compliance (Priority: High)

- **Schema & GAS Validation**  
  - Validate mapped data against GAS models (Pydantic) and against the target DPP standard.[1]
  - Enforce sector‑specific constraints (e.g. mandatory sustainability fields for Battery DPP).

- **Error Reporting**  
  - Generate clear, actionable validation reports, indicating whether errors arise at the ontology‑to‑GAS stage or GAS‑to‑schema stage.

### DPP Generation & Export (Priority: High)

- **DPP Generation**  
  - Create DPPs in required standard formats (JSON‑LD primary, XML as needed) from GAS representations.

- **Multi‑schema Export**  
  - Support generating multiple views from a single GAS instance, e.g.:  
    - EU DPP JSON‑LD.  
    - ECLASS16 XML‑based product sheet.  
    - ISA‑95 work definition for repairs (reverse flow).

- **Export Functionality**  
  - Allow users to export DPPs and schema‑specific files for submission, sharing, or MES integration.

### Interoperability & Extensibility (Priority: Medium)

- **Plugin / Adapter Architecture**  
  - Enable users to add support for new standards or custom schemas by implementing:  
    - Input adapter: Schema X → GAS.  
    - Output adapter: GAS → Schema Y.

- **Schema Registry**  
  - Provide an API for registering new schemas, their metadata, and mapping modules in `schema_registry.py`.

- **Documentation & API Reference**  
  - Comprehensive documentation for developers and contributors, including examples of new ontology adapters.

### User Experience & Onboarding (Priority: Medium)

- **Guided Onboarding**  
  - Step‑by‑step onboarding for first‑time users, including selection of sector (battery, textiles, generic) and input schema type.

- **Example Projects**  
  - Include sample data and example mappings that demonstrate ISA‑95 → GAS → Battery DPP and ECLASS16 → GAS → Generic DPP.

***

## User Experience

### Entry Point & First‑Time User Experience

- Users discover ReMake DPP via PyPI, GitHub, or a project website.
- Installation instructions guide users to install via pip and select their product sector and input schema.
- Guided onboarding walks users through setting up a working directory, loading sample data, choosing “input schema → GAS → output schema” flow.
- Starter kits/templates are offered for the selected DPP standard and ontology combination.

### Core Experience

- **Step 1:** User places their business data files (CSV, JSON, XML, ISA‑95 XML, ECLASS16 XML) in a designated working directory.
  - Validation checks for file presence, supported formats, and declared input schema.

- **Step 2:** User launches the mapping tool (CLI or web UI) to map their data fields to GAS and then to the DPP schema.
  - UI highlights ontology‑level mappings and offers defaults based on starter kits.

- **Step 3:** User runs validation on the mapped data at both GAS and target schema level.
  - Errors are grouped by stage (input parsing, GAS model validation, DPP schema validation).

- **Step 4:** User generates the DPP file in the required format and any additional schema views (e.g. ECLASS16 export).

- **Step 5:** User reviews and exports the DPP for submission or sharing, optionally generating ISA‑95 work definitions from a GAS/DPP instance for repair workflows.

***

## Narrative

In a mid‑sized manufacturing company producing industrial machinery and battery modules, the IT team faces mounting pressure to comply with new Digital Product Passport regulations while managing data across MES (ISA‑95), PLM, and ECLASS‑based component catalogues. Their product data is scattered across spreadsheets, ISA‑95 XML exports, and vendor ECLASS16 descriptions, and the team is overwhelmed by the complexity of mapping this data to evolving DPP standards.

With ReMake DPP, the developer installs the package from PyPI and follows clear documentation explaining DPPs, available standards, and supported schemas. They select an onboarding path “ISA‑95 + ECLASS16 input → GAS → Battery DPP JSON‑LD”, load example ISA‑95 B2MML and ECLASS16 XML into a working directory, and use the mapping tool to align fields to the internal GAS Identity, Structure, Lifecycle, and Sustainability layers.

The built‑in validators ensure that the GAS models are complete and consistent before exporting Battery DPPs, Generic DPPs, or sector‑specific reports, and the same GAS instances can produce ISA‑95 repair work orders for future circular‑economy workflows. Within hours, the team generates fully compliant DPP files and supporting schema views, ready for submission and internal integration. The business benefits from faster compliance, reduced risk, and a reusable, ontology‑agnostic framework that can be extended to new product lines and standards with minimal incremental effort.

***

## Technical Architecture (Reference)

The earlier technical architecture for connectors, mapping engine, exporters, and models remains applicable, with GAS now explicitly represented by `model.py` and `part_class.py`, and the schema registry coordinating mappings between input schemas, GAS, and DPP/export schemas.
