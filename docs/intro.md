---
title: Introduction
description: Overview of DPP Bridge / nmis_dpp
---

# Introduction

**DPP Bridge** (Python package `nmis_dpp`) is an open source ETL and harmonisation
layer for **Digital Product Passports (DPPs)**.

It ingests product and manufacturing data in multiple schemas and ontologies
(e.g. ISA‑95/B2MML, ECLASS 16), normalises it into an internal
**General Architectural Schema (GAS)**, and then exports:

- EU‑style DPPs (JSON‑LD as the primary format)
- Domain views like ECLASS‑based product sheets
- ISA‑95‑compatible views for MES/operations

Core design ideas:

- **GAS as hidden canonical model**: implemented in `nmis_dpp.model` and
  `nmis_dpp.part_class`, spanning identity, structure, lifecycle, risk,
  sustainability, and provenance.[cite:20]
- **Ontology‑aware mapping**: build mappings from ECLASS 16 XML and ISA‑95 XSDs
  using the helper scripts:
  - `nmis_dpp/eclass_build_mapping.py`
  - `nmis_dpp/isa95_build_mapping.py`
- **Schema registry & plug‑in mappers**: `nmis_dpp.schema_registry.SchemaRegistry`
  manages schema mappers like `ECLASSMapper` and `ISA95Mapper` in
  `nmis_dpp/mappers/`, so new schemas can be added without changing GAS.[cite:24]

Use this documentation to:

- Understand the GAS layers and part classes.
- See how ECLASS and ISA‑95 ontologies are mapped into GAS.
- Learn how to generate DPP outputs programmatically from Python.
