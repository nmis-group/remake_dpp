---
title: Quickstart
description: Get up and running with DPP Bridge / nmis_dpp
---

# Quickstart

## 1. Install

Use `pip` to install the package:

```bash
pip install remake_dpp
```

Or for local development:

```bash
git clone git@github.com:nmis-group/remake_dpp.git
cd remake_dpp
pip install -e .
```

## 2. Generate ontology → GAS mappings

Before using ECLASS or ISA‑95 mappers, generate the mapping YAMLs:

```bash 
cd nmis_dpp_test

# ECLASS → GAS mappings (outputs eclass_part_class_mapping.yaml)
python3 -m nmis_dpp.eclass_build_mapping

# ISA‑95 / B2MML → GAS mappings (outputs isa95_part_class_mapping.yaml)
python3 -m nmis_dpp.isa95_build_mapping

```
These YAML files live at the repo root and are used by ECLASSMapper and
ISA95Mapper to bind ontology concepts to PartClass types.

## 3. Create a basic Digital Product Passport - Run the example

```bash
python3 usage.py coffee_machine.json ECLASS
# python usage.py coffee_machine.json ISA-95

```


