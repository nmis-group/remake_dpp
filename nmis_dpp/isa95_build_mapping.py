"""
isa95_build_mapping.py

Parses all ISA-95 / B2MML XSD schemas from
./ontology_data/isa95/Schema and generates a YAML mapping that connects
domain PartClass types to ISA-95 element/complexType definitions,
using description-based scoring heuristics on XSD annotations.

Output YAML has the shape:

isa95_source: "xsd"
total_definitions: N
domain_mappings:
  PowerConversion:
    domain_class: PowerConversion
    isa95_type_ids: [...]
    isa95_types: { type_name: {name, description, group, source}, ... }

Author: Anmol Kumar
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Any, Optional

import xml.etree.ElementTree as ET
import yaml

from .part_class import PartClass


# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

ISA95_SCHEMA_DIR = (
    Path(__file__).resolve().parent
    / "ontology_data"
    / "isa95"
    / "Schema"
)

OUTPUT_YAML = "isa95_part_class_mapping.yaml"

MIN_SCORE = 1  # minimal keyword hits to accept a domain


# ---------------------------------------------------------------------------
# Domain keyword heuristics
# ---------------------------------------------------------------------------

DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "PowerConversion": [
        "transformer",
        "inverter",
        "rectifier",
        "power supply",
        "power-supply",
        "converter",
        "converter unit",
        "ac/dc",
        "dc/dc",
        "uninterruptible power supply",
        "ups",
        "voltage regulator",
        "energy",
        "power",
    ],
    "EnergyStorage": [
        "battery",
        "energy storage",
        "accumulator",
        "cell",
        "storage tank",
        "reservoir",
        "silo",
        "storage",
        "storage zone",
        "storage unit",
    ],
    "Actuator": [
        "actuator",
        "drive",
        "servo",
        "motion",
        "positioning",
        "valve actuator",
        "controlled element",
        "mechanical output",
        "execution",
    ],
    "Sensor": [
        "sensor",
        "transducer",
        "measuring device",
        "detector",
        "measurement",
        "measurement device",
        "instrument",
        "test",
        "sample",
        "quality",
        "result",
        "value",
    ],
    "ControlUnit": [
        "controller",
        "control unit",
        "control system",
        "control function",
        "logic controller",
        "plc",
        "programmable controller",
        "automation controller",
        "control",
        "module",
        "logic",
        "capability",
        "process code",
    ],
    "UserInterface": [
        "user interface",
        "operator",
        "hmi",
        "display",
        "panel",
        "annunciator",
        "alarm panel",
        "operator station",
        "person",
        "personnel",
        "individual",
    ],
    "Thermal": [
        "heating",
        "cooling",
        "thermal",
        "heat exchanger",
        "furnace",
        "oven",
        "kiln",
        "heater",
        "cooler",
        "temperature",
    ],
    "Fluidics": [
        "pump",
        "compressor",
        "valve",
        "pipeline",
        "pipe",
        "duct",
        "fluid",
        "hydraulic",
        "pneumatic",
        "liquid",
        "gas",
        "flow",
    ],
    "Structural": [
        "structure",
        "frame",
        "support",
        "foundation",
        "housing",
        "enclosure",
        "chassis",
        "platform",
        "physical asset",
        "asset",
        "class",
    ],
    "Transmission": [
        "gear",
        "gearbox",
        "transmission",
        "drive train",
        "belt drive",
        "chain drive",
        "shaft",
        "coupling",
        "bearing",
        "assembly",
    ],
    "Protection": [
        "protection",
        "protective",
        "fuse",
        "circuit breaker",
        "breaker",
        "protector",
        "safety device",
        "interlock",
        "safety interlock",
        "safety",
        "alarm",
        "alert",
        "security",
    ],
    "Connectivity": [
        "connector",
        "connection",
        "terminal",
        "terminal block",
        "i/o point",
        "communication link",
        "network connection",
        "bus",
        "fieldbus",
        "network",
        "resource network",
        "interface",
    ],
    "SoftwareModule": [
        "software",
        "software component",
        "application",
        "program",
        "execution logic",
        "algorithm",
        "recipe logic",
        "job",
        "order",
        "command",
        "transaction",
        "dispatch",
    ],
    "Consumable": [
        "consumable",
        "material",
        "ingredient",
        "feedstock",
        "raw material",
        "lubricant",
        "cleaning",
        "consumed",
        "produced",
        "lot",
        "sublot",
        "inventory",
        "bill of material",
    ],
    "Fastener": [
        "fastener",
        "bolt",
        "screw",
        "nut",
        "washer",
        "anchor",
        "clamp",
        "joint",
    ]
}


# ---------------------------------------------------------------------------
# XSD parsing helpers
# ---------------------------------------------------------------------------

XS_NS = "http://www.w3.org/2001/XMLSchema"
XS = "{%s}" % XS_NS


def _strip_ws(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def parse_xsd_file(path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Parse a single XSD file and extract named elements and complexTypes with
    their (optional) documentation text.

    Returns:
        defs_by_name: {
           type_name: {
              "name": type_name,
              "description": "...",
              "group": "Element" | "ComplexType",
              "source": "filename.xsd",
           },
           ...
        }
    """
    defs: Dict[str, Dict[str, Any]] = {}

    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except Exception as exc:
        print(f"⚠️  Failed to parse XSD {path.name}: {exc}")
        return defs

    # Elements
    for elem in root.findall(f".//{XS}element"):
        name = elem.get("name")
        if not name:
            continue

        doc_texts = []
        for ann in elem.findall(f"{XS}annotation"):
            for doc in ann.findall(f"{XS}documentation"):
                if doc.text:
                    doc_texts.append(doc.text)

        desc = _strip_ws(" ".join(doc_texts))

        defs[name] = {
            "name": name,
            "description": desc,
            "group": "Element",
            "source": path.name,
        }

    # Complex types
    for ctype in root.findall(f".//{XS}complexType"):
        name = ctype.get("name")
        if not name:
            continue

        doc_texts = []
        for ann in ctype.findall(f"{XS}annotation"):
            for doc in ann.findall(f"{XS}documentation"):
                if doc.text:
                    doc_texts.append(doc.text)

        desc = _strip_ws(" ".join(doc_texts))

        defs[name] = {
            "name": name,
            "description": desc,
            "group": "ComplexType",
            "source": path.name,
        }

    return defs


def load_all_xsd_definitions(schema_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Walk the Schemas directory and parse all .xsd files, merging the
    extracted definitions by name. Last definition wins on name clashes.
    """
    all_defs: Dict[str, Dict[str, Any]] = {}

    if not schema_dir.exists():
        print(f"❌ Schema directory not found: {schema_dir}")
        return all_defs

    for path in sorted(schema_dir.glob("*.xsd")):
        print(f"📂 Parsing XSD: {path.name}")
        defs = parse_xsd_file(path)
        all_defs.update(defs)

    return all_defs


# ---------------------------------------------------------------------------
# Scoring and classification
# ---------------------------------------------------------------------------

def domain_score(description: str, domain: str) -> int:
    text = (description or "").lower()
    score = 0
    for kw in DOMAIN_KEYWORDS.get(domain, []):
        if kw.lower() in text:
            score += 1
    return score


def classify_domain(description: str) -> Optional[str]:
    scores: Dict[str, int] = {}
    for domain in DOMAIN_KEYWORDS.keys():
        s = domain_score(description, domain)
        if s > 0:
            scores[domain] = s

    if not scores:
        return None

    best_domain = max(scores, key=scores.get)
    if scores[best_domain] < MIN_SCORE:
        return None
    return best_domain


def build_domain_mapping(
    defs_by_name: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Map domain PartClass types to ISA-95 XSD definitions.
    """
    domain_for_type: Dict[str, str] = {}

    for type_name, meta in defs_by_name.items():
        desc = meta.get("description", "")
        domain = classify_domain(desc)
        if domain is not None:
            domain_for_type[type_name] = domain

    part_class_mapping: Dict[str, Any] = {}
    for domain_class in DOMAIN_KEYWORDS.keys():
        part_class_mapping[domain_class] = {
            "domain_class": domain_class,
            "isa95_type_ids": [],
            "isa95_types": {},
        }

    for type_name, domain in domain_for_type.items():
        meta = defs_by_name[type_name]
        mapping = part_class_mapping[domain]
        mapping["isa95_types"][type_name] = meta
        mapping["isa95_type_ids"].append(type_name)

    for mapping in part_class_mapping.values():
        mapping["isa95_type_ids"] = sorted(mapping["isa95_type_ids"])

    return part_class_mapping


# ---------------------------------------------------------------------------
# Example PartClass bindings
# ---------------------------------------------------------------------------

def generate_part_class_bindings(mapping: Dict[str, Any]) -> List[PartClass]:
    examples: List[PartClass] = []

    for domain_class_name, isa_mapping in mapping.items():
        type_ids: List[str] = isa_mapping.get("isa95_type_ids", [])
        type_meta: Dict[str, Any] = isa_mapping.get("isa95_types", {})

        part = PartClass(
            part_id=f"{domain_class_name.lower()}-isa95-example-001",
            name=f"Example {domain_class_name} (ISA-95 XSD)",
            type=domain_class_name,
            properties={"example": True, "ontology": "ISA-95"},
        )

        part.bind_ontology(
            ontology_name="ISA-95",
            class_ids=type_ids,
            case_item_ids=[],
            metadata={
                "source": "xsd",
                "total_types": len(type_ids),
                "types": type_meta,
            },
        )

        examples.append(part)

    return examples


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"🔍 Loading ISA-95 XSDs from: {ISA95_SCHEMA_DIR}")

    defs_by_name = load_all_xsd_definitions(ISA95_SCHEMA_DIR)
    print(f"   Total extracted XSD definitions: {len(defs_by_name)}")

    print("🏗️ Building domain mappings (description-based scoring)...")
    part_class_mapping = build_domain_mapping(defs_by_name)

    print("💾 Saving mapping to YAML...")
    with open(OUTPUT_YAML, "w", encoding="utf-8") as f:
        yaml.dump(
            {
                "isa95_source": "xsd",
                "total_definitions": len(defs_by_name),
                "domain_mappings": part_class_mapping,
            },
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    print(f"✅ Mapping saved: {OUTPUT_YAML}")

    examples = generate_part_class_bindings(part_class_mapping)
    print("\n📋 Example usage:")
    for part in examples[:3]:
        binding = part.get_binding("ISA-95")
        if binding:
            print(f"  {part.type}: {len(binding.class_ids)} ISA-95 types")
            print(f"    example types: {binding.class_ids[:3]}...")
        else:
            print(f"  {part.type}: no ISA-95 binding")


if __name__ == "__main__":
    main()
