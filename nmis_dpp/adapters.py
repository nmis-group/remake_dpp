"""
adapters.py

Input adapters that parse source data files and build DigitalProductPassport
objects from ECLASS 16 XML, ISA-95 / B2MML XML, and CSV sources.

Public API
----------
build_dpp_from_eclass(files, config)     -> DigitalProductPassport
build_dpp_from_isa95(files, config)      -> DigitalProductPassport
build_dpp_from_csv(files, mapping_yml)   -> DigitalProductPassport

Each adapter:
  1. Parses the source data.
  2. Populates IdentityLayer, StructureLayer (incl. PartClass instances),
     LifecycleLayer, RiskLayer, SustainabilityLayer, and ProvenanceLayer.
  3. Returns a complete DigitalProductPassport.

Config schema (ECLASS and ISA-95 adapters)
------------------------------------------
An optional dict of product-level defaults/overrides.  All keys are optional:

    {
        "identity": {
            "global_ids": {"gtin": "...", "serial": "...", "manufacturer_pn": "..."},
            "make_model":  {"brand": "...", "model": "...", "hardware_rev": "..."},
            "ownership":   {"manufacturer": "...", "owner": "...", "location": "..."},
            "conformity":  ["CE", "RoHS", ...]
        },
        "lifecycle": {
            "manufacture": {"date": "...", "lot": "...", "factory": "..."}
        },
        "sustainability": {"mass": 0.0},
        "hierarchy": {"product": "MyProduct", ...}
    }

CSV mapping YAML schema
-----------------------
A YAML file passed via mapping_yml.  All keys are optional:

    identity:
      global_ids:  {gtin: "GTIN Column", serial: "Serial Column"}
      make_model:  {brand: "Brand Column", model: "Model Column"}
      ownership:   {manufacturer: "Manufacturer Column"}
      conformity:  "Certifications"     # comma-separated cell value
    parts:                               # one CSV row = one part
      part_id:   "Part ID"
      name:      "Name"
      type:      "Type"
      properties:
        - {column: "Voltage", key: "voltage"}
        - {column: "Mass (kg)", key: "mass"}
    lifecycle:
      manufacture: {date: "Manufacture Date", lot: "Lot", factory: "Factory"}
    sustainability:
      mass: "Total Mass (kg)"            # numeric; first non-null value used
"""

from __future__ import annotations

import csv
import dataclasses
import logging
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import yaml

from .eclass_build_mapping import (
    build_domain_mapping as _eclass_build_domain_mapping,
    parse_eclass_xml,
)
from .isa95_build_mapping import classify_domain as _isa95_classify_domain
from .model import (
    DigitalProductPassport,
    IdentityLayer,
    LifecycleLayer,
    ProvenanceLayer,
    RiskLayer,
    StructureLayer,
    SustainabilityLayer,
)
from .part_class import (
    Actuator,
    Connectivity,
    Consumable,
    ControlUnit,
    EnergyStorage,
    Fastener,
    Fluidics,
    PartClass,
    PowerConversion,
    Protection,
    Sensor,
    SoftwareModule,
    Structural,
    Thermal,
    Transmission,
    UserInterface,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PartClass type string → subclass registry
# ---------------------------------------------------------------------------

_PART_CLASS_REGISTRY: Dict[str, type] = {
    "PowerConversion": PowerConversion,
    "EnergyStorage": EnergyStorage,
    "Actuator": Actuator,
    "Sensor": Sensor,
    "ControlUnit": ControlUnit,
    "UserInterface": UserInterface,
    "Thermal": Thermal,
    "Fluidics": Fluidics,
    "Structural": Structural,
    "Transmission": Transmission,
    "Protection": Protection,
    "Connectivity": Connectivity,
    "SoftwareModule": SoftwareModule,
    "Consumable": Consumable,
    "Fastener": Fastener,
}

# ---------------------------------------------------------------------------
# Shared type aliases
# ---------------------------------------------------------------------------

FilesArg = Union[str, Path, Sequence[Union[str, Path]]]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalise_files(files: FilesArg) -> List[Path]:
    """Accept a single path or a sequence of paths; return a list of Paths."""
    if isinstance(files, (str, Path)):
        return [Path(files)]
    return [Path(f) for f in files]


def _make_part(
    part_id: str,
    name: str,
    part_type: str,
    properties: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> PartClass:
    """
    Instantiate the most specific PartClass subclass for *part_type*.

    Fields present in *extra* that match a typed attribute of the subclass are
    forwarded to the constructor; all remaining extra keys land in *properties*.

    Args:
        part_id:    Unique identifier for the part instance.
        name:       Human-readable name.
        part_type:  PartClass type string (e.g. "Actuator", "Sensor").
        properties: Free-form key/value properties dict.
        extra:      Additional fields; typed ones are routed to subclass attrs.

    Returns:
        An instance of the appropriate PartClass subclass (or PartClass itself
        if *part_type* is not in the registry).
    """
    cls = _PART_CLASS_REGISTRY.get(part_type, PartClass)
    props: Dict[str, Any] = dict(properties or {})
    extra_copy: Dict[str, Any] = dict(extra or {})

    if cls is not PartClass:
        # Determine which extra keys are valid typed fields on the subclass
        base_fields = {"part_id", "name", "type", "properties", "ontology_bindings"}
        valid_typed = {f.name for f in dataclasses.fields(cls)} - base_fields
        typed_kwargs: Dict[str, Any] = {}
        for key in list(extra_copy.keys()):
            if key in valid_typed:
                typed_kwargs[key] = extra_copy.pop(key)
        # Unmatched extra keys go into properties
        props.update(extra_copy)
        return cls(
            part_id=part_id,
            name=name,
            type=part_type,
            properties=props,
            **typed_kwargs,
        )

    props.update(extra_copy)
    return PartClass(part_id=part_id, name=name, type=part_type, properties=props)


def _identity_from_config(cfg: Dict[str, Any]) -> IdentityLayer:
    id_cfg = cfg.get("identity", {})
    return IdentityLayer(
        global_ids=dict(id_cfg.get("global_ids", {})),
        make_model=dict(id_cfg.get("make_model", {})),
        ownership=dict(id_cfg.get("ownership", {})),
        conformity=list(id_cfg.get("conformity", [])),
    )


def _lifecycle_from_config(cfg: Dict[str, Any]) -> LifecycleLayer:
    lc_cfg = cfg.get("lifecycle", {})
    return LifecycleLayer(
        manufacture=dict(lc_cfg.get("manufacture", {})),
        use={},
        serviceability={},
        events=[],
        end_of_life={},
    )


def _sustainability_from_config(cfg: Dict[str, Any]) -> SustainabilityLayer:
    sus_cfg = cfg.get("sustainability", {})
    return SustainabilityLayer(
        mass=float(sus_cfg.get("mass", 0.0)),
        energy={},
        recycled_content={},
        remanufacture={},
    )


def _empty_risk() -> RiskLayer:
    return RiskLayer(criticality={}, fmea=[], security={})


def _empty_provenance() -> ProvenanceLayer:
    return ProvenanceLayer(signatures=[], trace_links=[])


# ---------------------------------------------------------------------------
# ECLASS 16 adapter
# ---------------------------------------------------------------------------

def build_dpp_from_eclass(
    files: FilesArg,
    config: Optional[Dict[str, Any]] = None,
) -> DigitalProductPassport:
    """
    Parse one or more ECLASS 16 XML dictionary files and build a DPP.

    The adapter uses the same domain-scoring heuristics as
    ``eclass_build_mapping`` to classify ECLASS categorization classes into
    PartClass domains (Actuator, Sensor, Thermal, …).  One PartClass instance
    is created per identified domain; its OntologyBinding carries the full list
    of matching ECLASS class IRDIs and item-level case-of identifiers.

    Product-level metadata (manufacturer, GTIN, serial number, etc.) that is
    not encoded in the ECLASS ontology must be supplied via *config*.

    Args:
        files:
            Single path or list of paths to ECLASS 16 XML dictionary files
            (e.g. ``ECLASS16_0_ASSET_EN_SG_*.xml``).
        config:
            Optional product-level defaults/overrides dict.  See module
            docstring for the accepted key structure.

    Returns:
        DigitalProductPassport with:
          - IdentityLayer populated from *config*.
          - StructureLayer with one PartClass per recognised ECLASS domain,
            each carrying a full ``ECLASS`` OntologyBinding.
          - LifecycleLayer, SustainabilityLayer populated from *config*.
          - RiskLayer and ProvenanceLayer left as empty scaffolds.
    """
    config = config or {}
    paths = _normalise_files(files)

    logger.info("build_dpp_from_eclass: parsing %d file(s).", len(paths))

    # --- 1. Parse all ECLASS XML files ---
    classes_by_id, case_of_mapping = parse_eclass_xml(paths)
    logger.debug("ECLASS: extracted %d class definitions.", len(classes_by_id))

    # --- 2. Build domain → ECLASS class mapping ---
    domain_mapping = _eclass_build_domain_mapping(classes_by_id, case_of_mapping)

    # --- 3. Create one PartClass per identified domain ---
    parts: List[PartClass] = []

    for domain_class, mapping in domain_mapping.items():
        eclass_classes: Dict[str, Any] = mapping.get("eclass_classes", {})
        if not eclass_classes:
            continue

        case_item_ids: List[str] = mapping.get("eclass_case_item_ids", [])

        # Use the first class as the representative name
        first_id = next(iter(eclass_classes))
        first_meta = eclass_classes[first_id]

        part = _make_part(
            part_id=f"eclass-{domain_class.lower()}-001",
            name=first_meta.get("name", domain_class),
            part_type=domain_class,
        )
        part.bind_ontology(
            ontology_name="ECLASS",
            class_ids=list(eclass_classes.keys()),
            case_item_ids=case_item_ids,
            metadata={
                "version": "16.0",
                "total_classes": len(eclass_classes),
                "total_case_items": len(case_item_ids),
                "classes": eclass_classes,
            },
        )
        parts.append(part)
        logger.debug(
            "ECLASS domain '%s': %d classes, %d case items.",
            domain_class, len(eclass_classes), len(case_item_ids),
        )

    logger.info("build_dpp_from_eclass: created %d part(s).", len(parts))

    # --- 4. Assemble layers ---
    hierarchy: Dict[str, Any] = dict(config.get("hierarchy", {}))
    if not hierarchy:
        hierarchy = {"source": "ECLASS 16", "files": [p.name for p in paths]}

    identity = _identity_from_config(config)
    if not identity.global_ids:
        identity.global_ids["uuid"] = str(uuid.uuid4())

    return DigitalProductPassport(
        identity=identity,
        structure=StructureLayer(
            hierarchy=hierarchy,
            parts=parts,
            interfaces=[],
            materials=[],
            bom_refs=[],
        ),
        lifecycle=_lifecycle_from_config(config),
        risk=_empty_risk(),
        sustainability=_sustainability_from_config(config),
        provenance=_empty_provenance(),
    )


# ---------------------------------------------------------------------------
# ISA-95 / B2MML adapter
# ---------------------------------------------------------------------------

_B2MML_NS = "http://www.mesa.org/xml/B2MML"
_B2MML = f"{{{_B2MML_NS}}}"


def _b2mml_text(elem: ET.Element, tag: str) -> str:
    """Return stripped text of a direct child element, with or without namespace."""
    child = elem.find(f"{_B2MML}{tag}")
    if child is None:
        child = elem.find(tag)  # fallback: no namespace prefix in file
    return (child.text or "").strip() if child is not None else ""


def _b2mml_properties(elem: ET.Element, prop_tag: str) -> Dict[str, Any]:
    """
    Extract {ID: coerced_value} pairs from B2MML <*Property> child elements.

    Numeric strings are coerced to int or float; all others remain as str.
    """
    props: Dict[str, Any] = {}
    children = elem.findall(f"{_B2MML}{prop_tag}") or elem.findall(prop_tag)
    for prop in children:
        prop_id = _b2mml_text(prop, "ID")
        raw_value = _b2mml_text(prop, "Value")
        if not prop_id:
            continue
        try:
            props[prop_id] = int(raw_value)
        except ValueError:
            try:
                props[prop_id] = float(raw_value)
            except ValueError:
                props[prop_id] = raw_value
    return props


def _parse_equipment_element(
    eq_elem: ET.Element,
    id_prefix: str,
) -> Optional[PartClass]:
    """
    Convert a B2MML ``<Equipment>`` or ``<ContainedEquipment>`` element into a
    PartClass instance.

    PartClass type resolution order:
      1. ``<EquipmentClassID>`` text, if it names a registered PartClass type.
      2. Domain classification of ``<Description>`` text via ISA-95 keyword
         scoring (``isa95_build_mapping.classify_domain``).
      3. Fall back to the base ``PartClass``.

    ISA-95 OntologyBinding is attached when ``<EquipmentClassID>`` is present.

    Args:
        eq_elem:   The ``<Equipment>`` XML element.
        id_prefix: Short prefix for the generated part_id string.

    Returns:
        A PartClass instance, or None if no ID could be determined.
    """
    eq_id = _b2mml_text(eq_elem, "ID")
    if not eq_id:
        return None

    description = _b2mml_text(eq_elem, "Description")
    equipment_class_id = _b2mml_text(eq_elem, "EquipmentClassID")
    equipment_level = _b2mml_text(eq_elem, "EquipmentLevel")

    # Determine PartClass type
    if equipment_class_id in _PART_CLASS_REGISTRY:
        part_type = equipment_class_id
    elif description:
        part_type = _isa95_classify_domain(description) or "PartClass"
    else:
        part_type = "PartClass"

    properties = _b2mml_properties(eq_elem, "EquipmentProperty")

    part = _make_part(
        part_id=f"{id_prefix}-{eq_id}",
        name=description or eq_id,
        part_type=part_type,
        properties=properties,
    )

    if equipment_class_id:
        part.bind_ontology(
            ontology_name="ISA-95",
            class_ids=[equipment_class_id],
            metadata={
                "source": "B2MML",
                "equipment_level": equipment_level,
            },
        )

    return part


def _parse_physical_asset(
    pa_elem: ET.Element,
) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """
    Extract identity overrides, lifecycle overrides, and a product name from a
    B2MML ``<PhysicalAsset>`` element.

    Returns:
        (identity_overrides, lifecycle_overrides, product_name)
    """
    identity: Dict[str, Any] = {}
    lifecycle: Dict[str, Any] = {}

    pa_id = _b2mml_text(pa_elem, "ID")
    manufacturer = _b2mml_text(pa_elem, "Manufacturer")
    mfr_provided_id = _b2mml_text(pa_elem, "ManufacturerProvidedID")
    description = _b2mml_text(pa_elem, "Description")
    asset_props = _b2mml_properties(pa_elem, "PhysicalAssetProperty")

    if pa_id:
        identity.setdefault("global_ids", {})["serial"] = pa_id
    if mfr_provided_id:
        identity.setdefault("global_ids", {})["manufacturer_pn"] = mfr_provided_id
    if manufacturer:
        identity.setdefault("ownership", {})["manufacturer"] = manufacturer

    for key in ("manufacture_date", "manufactureDate", "production_date"):
        if key in asset_props:
            lifecycle.setdefault("manufacture", {})["date"] = str(asset_props[key])

    return identity, lifecycle, description


def build_dpp_from_isa95(
    files: FilesArg,
    config: Optional[Dict[str, Any]] = None,
) -> DigitalProductPassport:
    """
    Parse one or more ISA-95 / B2MML XML instance files and build a DPP.

    Recognised B2MML elements (namespace ``http://www.mesa.org/xml/B2MML``):

    * ``<PhysicalAsset>`` – product-level identity (serial, manufacturer,
      description) and physical-asset properties.
    * ``<Equipment>`` / ``<ContainedEquipment>`` – components converted to
      typed PartClass instances with ISA-95 OntologyBindings.
    * ``<WorkRequest>`` – lot / batch references added to LifecycleLayer and
      bom_refs.

    PartClass type is determined from ``<EquipmentClassID>`` (if it matches a
    registered type) or from ISA-95 keyword-scoring of ``<Description>``.
    Numeric ``<EquipmentProperty>`` values are coerced to int / float.

    Values extracted from XML are merged with *config*; *config* takes
    precedence on any key conflict.

    Args:
        files:
            Single path or list of paths to B2MML XML instance files.
        config:
            Optional product-level defaults/overrides dict.

    Returns:
        DigitalProductPassport with:
          - IdentityLayer from PhysicalAsset elements merged with *config*.
          - StructureLayer with one PartClass per Equipment element.
          - LifecycleLayer populated from WorkRequest IDs and PhysicalAsset
            properties, merged with *config*.
          - RiskLayer and ProvenanceLayer left as empty scaffolds.
    """
    config = config or {}
    paths = _normalise_files(files)

    logger.info("build_dpp_from_isa95: parsing %d file(s).", len(paths))

    parts: List[PartClass] = []
    identity_xml: Dict[str, Any] = {}
    lifecycle_xml: Dict[str, Any] = {}
    hierarchy: Dict[str, Any] = dict(config.get("hierarchy", {}))
    bom_refs: List[str] = []

    for path in paths:
        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            logger.error("Failed to parse '%s': %s", path, exc)
            continue

        root = tree.getroot()
        root_local = root.tag.replace(_B2MML, "")

        # --- Equipment elements (all depths, deduplicated by element identity) ---
        seen: set = set()

        def _collect_equipment(search_root: ET.Element) -> None:
            for tag in ("Equipment", "ContainedEquipment"):
                for eq in search_root.findall(f".//{_B2MML}{tag}") + (
                    [search_root] if root_local == tag else []
                ):
                    if id(eq) in seen:
                        continue
                    seen.add(id(eq))
                    prefix = "ceq" if tag == "ContainedEquipment" else "eq"
                    part = _parse_equipment_element(eq, prefix)
                    if part is not None:
                        parts.append(part)

        _collect_equipment(root)

        # --- PhysicalAsset → identity / lifecycle ---
        pa_elements = root.findall(f".//{_B2MML}PhysicalAsset")
        if root_local == "PhysicalAsset":
            pa_elements = [root] + pa_elements

        for pa in pa_elements:
            id_overrides, lc_overrides, description = _parse_physical_asset(pa)
            # Merge XML values (later files do not overwrite earlier ones)
            for key, sub in id_overrides.items():
                identity_xml.setdefault(key, {}).update(sub)
            for key, sub in lc_overrides.items():
                lifecycle_xml.setdefault(key, {}).update(sub)
            if not hierarchy and description:
                hierarchy["product"] = description

        # --- WorkRequest → lot reference ---
        for wr in root.findall(f".//{_B2MML}WorkRequest"):
            wr_id = _b2mml_text(wr, "ID")
            if wr_id:
                lifecycle_xml.setdefault("manufacture", {}).setdefault("lot", wr_id)
                bom_refs.append(wr_id)

    logger.info("build_dpp_from_isa95: created %d part(s).", len(parts))

    # --- Merge: config takes precedence over XML-extracted values ---
    cfg_id = config.get("identity", {})
    cfg_lc = config.get("lifecycle", {})

    merged_config: Dict[str, Any] = {
        "identity": {
            "global_ids": {**identity_xml.get("global_ids", {}),
                           **cfg_id.get("global_ids", {})},
            "make_model":  dict(cfg_id.get("make_model", {})),
            "ownership":   {**identity_xml.get("ownership", {}),
                            **cfg_id.get("ownership", {})},
            "conformity":  list(cfg_id.get("conformity", [])),
        },
        "lifecycle": {
            "manufacture": {**lifecycle_xml.get("manufacture", {}),
                            **cfg_lc.get("manufacture", {})},
        },
        "sustainability": config.get("sustainability", {}),
    }

    if not merged_config["identity"]["global_ids"]:
        merged_config["identity"]["global_ids"]["uuid"] = str(uuid.uuid4())

    if not hierarchy:
        hierarchy = {"source": "ISA-95", "files": [p.name for p in paths]}

    return DigitalProductPassport(
        identity=_identity_from_config(merged_config),
        structure=StructureLayer(
            hierarchy=hierarchy,
            parts=parts,
            interfaces=[],
            materials=[],
            bom_refs=bom_refs,
        ),
        lifecycle=_lifecycle_from_config(merged_config),
        risk=_empty_risk(),
        sustainability=_sustainability_from_config(merged_config),
        provenance=_empty_provenance(),
    )


# ---------------------------------------------------------------------------
# CSV adapter
# ---------------------------------------------------------------------------

def _load_mapping_yml(mapping_yml: Union[str, Path]) -> Dict[str, Any]:
    path = Path(mapping_yml)
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _col(row: Dict[str, str], col_name: Optional[str]) -> str:
    """Return a stripped CSV cell value; return empty string if column absent."""
    if not col_name:
        return ""
    return row.get(col_name, "").strip()


def _try_float(value: str) -> Optional[float]:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def build_dpp_from_csv(
    files: FilesArg,
    mapping_yml: Union[str, Path],
) -> DigitalProductPassport:
    """
    Parse one or more CSV files and build a DPP using a YAML column mapping.

    Each CSV row becomes one part in the StructureLayer.  Product-level fields
    (identity, lifecycle, sustainability) are extracted from whichever row
    first contains a non-empty value for the mapped column.

    Part type resolution: the cell in the column mapped to ``parts.type`` is
    matched against the PartClass registry (case-sensitive).  Unrecognised
    types fall back to the base ``PartClass``.

    Additional typed attributes (e.g. ``voltage``, ``torque``) can be
    forwarded to subclass constructors via ``parts.properties`` entries in the
    mapping YAML; keys that match a subclass field are routed there
    automatically.

    Args:
        files:
            Single path or list of paths to UTF-8 comma-delimited CSV files.
        mapping_yml:
            Path to a YAML column-mapping file.  See module docstring for the
            full schema.

    Returns:
        DigitalProductPassport with all layers populated from CSV data.

    Raises:
        FileNotFoundError: if *mapping_yml* does not exist.
    """
    paths = _normalise_files(files)
    mapping = _load_mapping_yml(mapping_yml)

    logger.info(
        "build_dpp_from_csv: parsing %d file(s) with mapping '%s'.",
        len(paths), mapping_yml,
    )

    # Mapping sub-dicts
    id_map: Dict[str, Any] = mapping.get("identity", {})
    parts_map: Dict[str, Any] = mapping.get("parts", {})
    lc_map: Dict[str, Any] = mapping.get("lifecycle", {})
    sus_map: Dict[str, Any] = mapping.get("sustainability", {})

    # Column name shortcuts
    gid_map: Dict[str, str] = id_map.get("global_ids", {})
    mm_map: Dict[str, str] = id_map.get("make_model", {})
    own_map: Dict[str, str] = id_map.get("ownership", {})
    conf_col: Optional[str] = id_map.get("conformity")
    mfr_map: Dict[str, str] = lc_map.get("manufacture", {})
    mass_col: Optional[str] = sus_map.get("mass")

    # Accumulated product-level values (first non-empty value per field wins)
    global_ids: Dict[str, str] = {}
    make_model: Dict[str, str] = {}
    ownership: Dict[str, str] = {}
    conformity: List[str] = []
    manufacture: Dict[str, Any] = {}
    total_mass: Optional[float] = None

    parts: List[PartClass] = []
    row_counter = 0

    for path in paths:
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                row_counter += 1

                # --- Product-level fields (first non-empty value wins) ---
                for field, col_name in gid_map.items():
                    if field not in global_ids:
                        val = _col(row, col_name)
                        if val:
                            global_ids[field] = val

                for field, col_name in mm_map.items():
                    if field not in make_model:
                        val = _col(row, col_name)
                        if val:
                            make_model[field] = val

                for field, col_name in own_map.items():
                    if field not in ownership:
                        val = _col(row, col_name)
                        if val:
                            ownership[field] = val

                if not conformity and conf_col:
                    raw = _col(row, conf_col)
                    if raw:
                        conformity = [c.strip() for c in raw.split(",") if c.strip()]

                for field, col_name in mfr_map.items():
                    if field not in manufacture:
                        val = _col(row, col_name)
                        if val:
                            manufacture[field] = val

                if total_mass is None and mass_col:
                    total_mass = _try_float(_col(row, mass_col))

                # --- Part ---
                part_id = _col(row, parts_map.get("part_id")) or f"part-{row_counter}"
                part_name = _col(row, parts_map.get("name")) or part_id
                part_type = _col(row, parts_map.get("type")) or "PartClass"

                # Collect typed/property values from mapped columns
                extra: Dict[str, Any] = {}
                for prop_spec in parts_map.get("properties", []):
                    col_name = prop_spec.get("column")
                    key = prop_spec.get("key")
                    if col_name and key:
                        raw = _col(row, col_name)
                        if raw:
                            numeric = _try_float(raw)
                            extra[key] = numeric if numeric is not None else raw

                parts.append(
                    _make_part(
                        part_id=part_id,
                        name=part_name,
                        part_type=part_type,
                        extra=extra,
                    )
                )

    logger.info(
        "build_dpp_from_csv: created %d part(s) from %d row(s).",
        len(parts), row_counter,
    )

    if not global_ids:
        global_ids["uuid"] = str(uuid.uuid4())

    return DigitalProductPassport(
        identity=IdentityLayer(
            global_ids=global_ids,
            make_model=make_model,
            ownership=ownership,
            conformity=conformity,
        ),
        structure=StructureLayer(
            hierarchy={"source": "CSV", "files": [p.name for p in paths]},
            parts=parts,
            interfaces=[],
            materials=[],
            bom_refs=[],
        ),
        lifecycle=LifecycleLayer(
            manufacture=manufacture,
            use={},
            serviceability={},
            events=[],
            end_of_life={},
        ),
        risk=_empty_risk(),
        sustainability=SustainabilityLayer(
            mass=total_mass or 0.0,
            energy={},
            recycled_content={},
            remanufacture={},
        ),
        provenance=_empty_provenance(),
    )
