"""
eclass_build_mapping.py

Parses ECLASS XML files from ./ontology_data/eclass_16/dictionary_assets_en and
generates a YAML mapping that connects domain PartClass types to ECLASS classes
and their allowable item types, using definition-based scoring heuristics.

Key changes vs. earlier version:
- Uses per-domain scores instead of boolean keyword hits.
- Classifies each ECLASS class across all domains, then assigns to the
  best-scoring domain above a threshold.
- Tightens PowerConversion behaviour to avoid swallowing unrelated classes.
"""

from __future__ import annotations

import yaml
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

from .part_class import PartClass

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

ECLASS_DIR = (
    Path(__file__).resolve().parent
    / "ontology_data"
    / "eclass_16"
    / "dictionary_assets_en"
)

OUTPUT_YAML = "eclass_part_class_mapping.yaml"

NS = {
    "dic": "urn:eclass:xml-schema:dictionary:5.0",
    "ontoml": "urn:iso:std:iso:is:13584:-32:ed-1:tech:xml-schema:ontoml",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}

# Minimum total keyword hits required to classify a class into ANY domain
MIN_SCORE = 2

# ---------------------------------------------------------------------------
# Domain keyword heuristics
# ---------------------------------------------------------------------------

DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "PowerConversion": [
        # Prefer more specific phrases rather than generic “power”, “voltage”, etc.
        "power supply",
        "power-supply",
        "power converter",
        "ac/dc converter",
        "dc/dc converter",
        "inverter",
        "rectifier",
        "uninterruptible power supply",
        "ups",
        "transformer",
    ],
    "EnergyStorage": [
        "battery",
        "accumulator",
        "energy storage",
        "cell",
        "capacitor",
        "supercapacitor",
    ],
    "Actuator": [
        "actuator",
        "drive",
        "servo",
        "motion",
        "positioning",
        "valve actuator",
    ],
    "Sensor": [
        "sensor",
        "transducer",
        "measuring device",
        "detector",
        "measurement",
        "temperature sensor",
        "pressure sensor",
        "flow sensor",
        "position sensor",
        "vibration sensor",
    ],
    "ControlUnit": [
        "controller",
        "control unit",
        "logic controller",
        "plc",
        "control system",
        "control device",
    ],
    "UserInterface": [
        "user interface",
        "operator panel",
        "display",
        "hmi",
        "control panel",
        "keypad",
    ],
    "Thermal": [
        "heating",
        "cooling",
        "thermal",
        "heat exchanger",
        "radiator",
        "heater",
        "fan",
    ],
    "Fluidics": [
        "fluid",
        "hydraulic",
        "pneumatic",
        "pump",
        "valve",
        "compressor",
    ],
    "Structural": [
        "structural",
        "frame",
        "housing",
        "support",
        "chassis",
        "enclosure",
        "bracket",
    ],
    "Transmission": [
        "gear",
        "gearing",
        "drive shaft",
        "drivetrain",
        "belt drive",
        "chain drive",
        "coupling",
        "bearing",
    ],
    "Protection": [
        "protection device",
        "fuse",
        "circuit breaker",
        "breaker",
        "protector",
        "surge protector",
        "overcurrent",
        "overvoltage",
    ],
    "Connectivity": [
        "connector",
        "plug",
        "socket",
        "cable",
        "terminal block",
        "interface",
        "bus system",
    ],
    "SoftwareModule": [
        "software",
        "firmware",
        "program",
        "control software",
        "software module",
    ],
    "Consumable": [
        "consumable",
        "filter",
        "lubricant",
        "oil",
        "grease",
        "sealant",
        "cleaning agent",
    ],
    "Fastener": [
        "fastener",
        "screw",
        "bolt",
        "nut",
        "washer",
        "rivet",
        "anchor bolt",
    ],
}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def extract_definition_text(class_elem: ET.Element) -> str:
    """
    Extract concatenated definition text from a class element.
    """
    parts: List[str] = []
    for def_elem in class_elem.findall("./definition"):
        for text_elem in def_elem.findall("./text"):
            if text_elem.text:
                parts.append(text_elem.text.strip())
    return " ".join(parts)


def parse_eclass_xml(
    xml_files: List[Path],
) -> Tuple[Dict[str, Any], Dict[str, List[str]]]:
    """
    Parse all ECLASS XML files into:
    - classes_by_id: {id: {id, name, type, definition, case_of?}}
    - case_of_mapping: {base_class_id: [item_class_ids]}
    """
    classes_by_id: Dict[str, Any] = {}
    case_of_mapping: Dict[str, List[str]] = {}

    for xml_file in xml_files:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        for class_elem in root.findall(".//ontoml:class", NS):
            class_id = class_elem.get("id")
            if not class_id:
                continue

            xsi_type = class_elem.get(f"{{{NS['xsi']}}}type", "")
            pref = class_elem.find("./preferred_name/label")
            name = (
                pref.text.strip()
                if pref is not None and pref.text
                else f"ECLASS Class {class_id}"
            )
            definition_text = extract_definition_text(class_elem)

            if xsi_type.endswith("CATEGORIZATION_CLASS_Type"):
                classes_by_id[class_id] = {
                    "id": class_id,
                    "name": name,
                    "type": "CATEGORIZATION",
                    "definition": definition_text,
                }

            elif xsi_type.endswith("ITEM_CLASS_CASE_OF_Type"):
                case_refs: List[str] = []
                for ic in class_elem.findall("./is_case_of"):
                    ref = ic.get("class_ref")
                    if ref:
                        case_refs.append(ref)
                classes_by_id[class_id] = {
                    "id": class_id,
                    "name": name,
                    "type": "ITEM",
                    "definition": definition_text,
                    "case_of": case_refs,
                }
                for ref in case_refs:
                    case_of_mapping.setdefault(ref, []).append(class_id)

    return classes_by_id, case_of_mapping


def domain_score(definition: str, domain: str) -> int:
    """
    Compute a simple score for how well a definition matches a given domain.

    Score = count of domain keywords found (case-insensitive, substring match).
    """
    text = (definition or "").lower()
    score = 0
    for kw in DOMAIN_KEYWORDS.get(domain, []):
        if kw.lower() in text:
            score += 1
    return score


def classify_domain_for_class(definition: str) -> Optional[str]:
    """
    Given a definition string, compute scores for all domains and return
    the best-matching domain if its score meets MIN_SCORE; otherwise None.
    """
    scores: Dict[str, int] = {}
    for domain in DOMAIN_KEYWORDS.keys():
        s = domain_score(definition, domain)
        if s > 0:
            scores[domain] = s

    if not scores:
        return None

    # Find domain(s) with highest score
    best_domain = max(scores, key=scores.get)
    best_score = scores[best_domain]

    if best_score < MIN_SCORE:
        return None

    return best_domain


def build_domain_mapping(
    classes_by_id: Dict[str, Any],
    case_of_mapping: Dict[str, List[str]],
) -> Dict[str, Any]:
    """
    Map domain PartClass types to ECLASS classes and their allowable items,
    using definition-based scoring across all domains.

    Returns:
        part_class_mapping: {
           "PowerConversion": {
               "domain_class": "PowerConversion",
               "eclass_class_ids": [],
               "eclass_case_item_ids": [...],
               "eclass_classes": { class_id: {..}, ... }
           },
           ...
        }
    """
    # First, decide a single best domain (or no domain) for each categorization class.
    domain_for_class: Dict[str, str] = {}

    for class_id, cls in classes_by_id.items():
        if cls.get("type") != "CATEGORIZATION":
            continue
        definition = cls.get("definition", "")
        domain = classify_domain_for_class(definition)
        if domain is not None:
            domain_for_class[class_id] = domain

    # Initialize mapping per domain
    part_class_mapping: Dict[str, Any] = {}
    for domain_class in DOMAIN_KEYWORDS.keys():
        part_class_mapping[domain_class] = {
            "domain_class": domain_class,
            "eclass_class_ids": [],  # kept for schema compatibility, but unused
            "eclass_case_item_ids": [],
            "eclass_classes": {},
        }

    # Fill eclass_classes for each domain
    for class_id, domain in domain_for_class.items():
        cls = classes_by_id.get(class_id)
        if not cls:
            continue
        mapping = part_class_mapping[domain]
        mapping["eclass_classes"][class_id] = cls

    # For each domain, compute union of ITEM classes whose base class belongs to that domain
    for domain_class, mapping in part_class_mapping.items():
        selected_base_ids = set(mapping["eclass_classes"].keys())
        all_case_items: set[str] = set()

        for base_id in selected_base_ids:
            for item_id in case_of_mapping.get(base_id, []):
                all_case_items.add(item_id)

        mapping["eclass_case_item_ids"] = sorted(all_case_items)

    return part_class_mapping


def generate_part_class_bindings(mapping: Dict[str, Any]) -> List[PartClass]:
    """
    Generate example PartClass instances with ECLASS bindings populated.

    class_ids is left empty because selection is semantic, not ID-driven.
    """
    examples: List[PartClass] = []

    for domain_class_name, eclass_mapping in mapping.items():
        part = PartClass(
            part_id=f"{domain_class_name.lower()}-example-001",
            name=f"Example {domain_class_name}",
            type=domain_class_name,
            properties={"example": True},
        )

        part.bind_ontology(
            ontology_name="ECLASS",
            class_ids=[],  # no explicit IDs; see metadata["classes"]
            case_item_ids=eclass_mapping["eclass_case_item_ids"],
            metadata={
                "version": "16.0",
                "total_items": len(eclass_mapping["eclass_case_item_ids"]),
                "classes": eclass_mapping["eclass_classes"],
            },
        )

        examples.append(part)

    return examples


def main() -> None:
    """
    Main entrypoint: parse ECLASS → generate mapping → save YAML.
    """
    print("🔍 Scanning ECLASS XML files...")
    xml_files = list(ECLASS_DIR.glob("*.xml"))
    if not xml_files:
        print(f"❌ No XML files found in {ECLASS_DIR}")
        return

    print(f"📖 Parsing {len(xml_files)} ECLASS files...")
    classes_by_id, case_of_mapping = parse_eclass_xml(xml_files)

    print("🏗️ Building domain mappings (definition-based scoring)...")
    part_class_mapping = build_domain_mapping(classes_by_id, case_of_mapping)

    print("💾 Saving mapping to YAML...")
    with open(OUTPUT_YAML, "w", encoding="utf-8") as f:
        yaml.dump(
            {
                "eclass_version": "16.0",
                "total_classes": len(classes_by_id),
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
        binding = part.get_binding("ECLASS")
        if binding:
            print(f"  {part.type}: {len(binding.case_item_ids)} ECLASS item types")
            print(f"    example item_ids: {binding.case_item_ids[:3]}...")
        else:
            print(f"  {part.type}: no ECLASS binding")


if __name__ == "__main__":
    main()
