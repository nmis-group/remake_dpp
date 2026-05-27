"""
api.py

High-level facade for the nmis_dpp package.

Single entry point that wires the input adapters, the GAS model, and the
schema registry together into one callable:

    result = create_dpp(
        input_schema  = "ECLASS",
        output_schema = "BatteryDPP",
        files         = [Path("ECLASS16_0_ASSET_EN_SG_13.xml")],
        config_dir    = Path("my_config/"),
    )

Supported input schemas
-----------------------
  "ECLASS"  / "eclass"  / "EC"      → build_dpp_from_eclass
  "ISA-95"  / "ISA95"   / "isa95"
  / "isa-95" / "IEC62264"            → build_dpp_from_isa95
  "CSV"     / "csv"                  → build_dpp_from_csv

Supported output schemas
------------------------
  Any schema registered in the global SchemaRegistry:
  "ECLASS", "ISA-95", "BatteryDPP" (and their aliases).
  Use list_output_schemas() to query at runtime.

Config directory layout
-----------------------
For ECLASS / ISA-95 input:
  config_dir/eclass_config.yml   (optional)
  config_dir/isa95_config.yml    (optional)
  → loaded as a dict and passed as config= to the adapter.
  → if the file is absent or config_dir is None, an empty dict is used.

For CSV input:
  config_dir/mapping.yml         (required)
  → passed as mapping_yml= to build_dpp_from_csv.
  → missing file raises ValueError.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from .adapters import (
    build_dpp_from_csv,
    build_dpp_from_eclass,
    build_dpp_from_isa95,
)
from .model import DigitalProductPassport
from .schema_registry import get_global_registry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Input schema dispatch table
# Keys are lower-cased at lookup time; values are adapter callables.
# ---------------------------------------------------------------------------

_INPUT_ADAPTER_MAP: Dict[str, Any] = {
    "eclass":   build_dpp_from_eclass,
    "ec":       build_dpp_from_eclass,
    "isa-95":   build_dpp_from_isa95,
    "isa95":    build_dpp_from_isa95,
    "iec62264": build_dpp_from_isa95,
    "csv":      build_dpp_from_csv,
}

# Canonical display names used by list_input_schemas()
_CANONICAL_INPUT_SCHEMAS: List[str] = ["ECLASS", "ISA-95", "CSV"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_adapter(input_schema: str):
    """
    Return the adapter callable for *input_schema*.

    Raises:
        ValueError: if *input_schema* is not recognised.
    """
    adapter = _INPUT_ADAPTER_MAP.get(input_schema.lower())
    if adapter is None:
        supported = ", ".join(_CANONICAL_INPUT_SCHEMAS)
        raise ValueError(
            f"Unknown input_schema {input_schema!r}. "
            f"Supported values: {supported}."
        )
    return adapter


def _load_adapter_config(
    input_schema: str,
    config_dir: Optional[Path],
) -> Dict[str, Any]:
    """
    Load optional YAML configuration for ECLASS / ISA-95 adapters.

    Convention:  config_dir/<schema_lower>_config.yml
      e.g.  eclass_config.yml  or  isa95_config.yml

    Returns an empty dict if the file is absent or config_dir is None.
    """
    if config_dir is None:
        return {}

    stub = input_schema.lower().replace("-", "")
    cfg_path = config_dir / f"{stub}_config.yml"

    if not cfg_path.exists():
        logger.debug("No adapter config found at %s; using empty config.", cfg_path)
        return {}

    with cfg_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    logger.info("Loaded adapter config from %s.", cfg_path)
    return data


def _resolve_mapping_yml(config_dir: Optional[Path]) -> Path:
    """
    Return the path to mapping.yml inside *config_dir*.

    Raises:
        ValueError: if config_dir is None or mapping.yml does not exist.
    """
    if config_dir is None:
        raise ValueError(
            "config_dir is required for CSV input — "
            "it must contain a mapping.yml file."
        )

    mapping_path = config_dir / "mapping.yml"
    if not mapping_path.exists():
        raise ValueError(
            f"CSV adapter requires a mapping.yml file, "
            f"but none was found at {mapping_path}."
        )

    return mapping_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_dpp(
    input_schema: str,
    output_schema: str,
    files: List[Union[str, Path]],
    config_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    End-to-end pipeline: parse source files → build DPP → map to output schema.

    Steps:
      1. Resolve the correct input adapter from *input_schema*.
      2. Load optional config / mapping YAML from *config_dir*.
      3. Call the adapter to build a ``DigitalProductPassport``.
      4. Use the global ``SchemaRegistry`` to map the DPP to *output_schema*.
      5. Return the mapped dict (JSON-LD ready).

    Args:
        input_schema:
            Source data format. Case-insensitive. Supported values:
            ``"ECLASS"``, ``"ISA-95"`` / ``"ISA95"``, ``"CSV"``.
        output_schema:
            Target schema name or alias recognised by the registry.
            Examples: ``"ECLASS"``, ``"ISA-95"``, ``"BatteryDPP"``,
            ``"battery"``.
        files:
            One or more paths to the source data files.
        config_dir:
            Optional directory containing configuration files:

            - ECLASS / ISA-95: ``<schema>_config.yml`` (optional).
            - CSV: ``mapping.yml`` (required).

    Returns:
        Dict[str, Any]: JSON-LD–ready mapped DPP document.

    Raises:
        ValueError: unknown *input_schema*, or missing ``mapping.yml`` for CSV.
        KeyError:   unknown *output_schema* (raised by the registry).
        ValueError: validation failure inside the target mapper.
    """
    if config_dir is not None:
        config_dir = Path(config_dir)

    files = [Path(f) for f in files]

    logger.info(
        "create_dpp: input=%r  output=%r  files=%d",
        input_schema, output_schema, len(files),
    )

    # 1. Resolve adapter
    adapter = _resolve_adapter(input_schema)

    # 2. Build DigitalProductPassport
    schema_key = input_schema.lower()
    if schema_key == "csv":
        mapping_yml = _resolve_mapping_yml(config_dir)
        dpp: DigitalProductPassport = adapter(files, mapping_yml)
    else:
        config = _load_adapter_config(input_schema, config_dir)
        dpp = adapter(files, config)

    logger.info(
        "create_dpp: DPP built — %d part(s) in structure.",
        len(dpp.structure.parts),
    )

    # 3. Map to output schema via registry
    registry = get_global_registry()
    mapped = registry.map_dpp(output_schema, dpp)

    logger.info("create_dpp: mapped to %r successfully.", output_schema)
    return mapped


def list_input_schemas() -> List[str]:
    """
    Return the canonical names of all supported input schemas.

    Returns:
        List[str]: ``["ECLASS", "ISA-95", "CSV"]``
    """
    return list(_CANONICAL_INPUT_SCHEMAS)


def list_output_schemas() -> List[str]:
    """
    Return the canonical names of all output schemas currently registered
    in the global SchemaRegistry.

    Returns:
        List[str]: e.g. ``["ECLASS", "ISA-95", "BatteryDPP"]``
    """
    return get_global_registry().list_schemas()
