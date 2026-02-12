"""
schema_registry.py

Central registry for all schema mappers in the nmis_dpp package.

Responsibilities:
- Keep track of all available schema mappers (ECLASS, ISA-95, etc.).
- Load per-schema configuration (from YAML) for all layers and part classes.
- Provide a single API to:
  - get a mapper,
  - map an entire DigitalProductPassport,
  - map individual parts,
  - list available schemas.

This file does NOT contain schema-specific logic; that lives in mapper classes
(e.g., ECLASSMapper, ISA95Mapper) which inherit from SchemaMapper.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Type, Optional, List, Any, Union

import yaml

from .schema_base import SchemaMapper
from .model import (
    DigitalProductPassport,
    IdentityLayer,
    StructureLayer,
    LifecycleLayer,
    RiskLayer,
    SustainabilityLayer,
    ProvenanceLayer,
)
from .part_class import PartClass

logger = logging.getLogger(__name__)


class SchemaRegistry:
    """
    Registry for managing schema mappers.

    - Each schema has:
        - a mapper class (subclass of SchemaMapper),
        - optional aliases (e.g., "ISA95" for "ISA-95"),
        - an optional configuration dictionary loaded from YAML.
    - This registry is the central entry point to:
        - get a mapper instance,
        - map a full DPP,
        - map individual parts,
        - list schemas and aliases.
    """

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """
        Initialize the schema registry.

        Args:
            config_dir: Directory containing YAML config files for schema mappings.
                        Defaults to <this_file_dir>/config.
        """
        if config_dir is None:
            config_dir = Path(__file__).parent / "config"

        self.config_dir: Path = config_dir

        # Canonical schema name -> mapper class or lazy loader callable
        self._mappers: Dict[str, Union[Type[SchemaMapper], Any]] = {}

        # Alias -> canonical schema name
        self._aliases: Dict[str, str] = {}

        # Canonical schema name -> instantiated mapper
        self._instances: Dict[str, SchemaMapper] = {}

        # Canonical schema name -> loaded config
        self._configs: Dict[str, Dict[str, Any]] = {}

        logger.info(f"SchemaRegistry initialized with config_dir={self.config_dir}")

    # -------------------------------------------------------------------------
    # Registration methods
    # -------------------------------------------------------------------------

    def register(self, mapper_class: Type[SchemaMapper], aliases: Optional[List[str]] = None) -> None:
        """
        Register a mapper class eagerly.

        Args:
            mapper_class: Concrete SchemaMapper subclass.
            aliases: Optional list of alias names for this schema.
        """
        if not issubclass(mapper_class, SchemaMapper):
            raise TypeError(f"{mapper_class} must inherit from SchemaMapper")

        tmp = mapper_class(config={})
        name = tmp.get_schema_name()

        self._mappers[name] = mapper_class
        logger.info(f"Registered schema mapper: {name}")

        if aliases:
            for alias in aliases:
                self._aliases[alias] = name
                logger.debug(f"Alias registered: {alias} -> {name}")

    def register_lazy(
        self,
        canonical_name: str,
        module_path: str,
        class_name: str,
        aliases: Optional[List[str]] = None,
    ) -> None:
        """
        Register a mapper lazily. The mapper class is imported only on first use.

        Args:
            canonical_name: Canonical schema name (e.g. "ECLASS", "ISA-95").
            module_path: Module path string (e.g. "nmis_dpp.mappers.eclass_mapper").
            class_name: Class name string in the module (e.g. "ECLASSMapper").
            aliases: Optional list of alias names (e.g. ["eclass", "EC"]).
        """

        def lazy_loader():
            logger.debug(f"Lazy loading mapper {canonical_name} from {module_path}.{class_name}")
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            if not issubclass(cls, SchemaMapper):
                raise TypeError(f"{class_name} in {module_path} is not a SchemaMapper")
            return cls

        self._mappers[canonical_name] = lazy_loader
        logger.info(f"Registered lazy mapper: {canonical_name}")

        if aliases:
            for alias in aliases:
                self._aliases[alias] = canonical_name
                logger.debug(f"Alias (lazy) registered: {alias} -> {canonical_name}")

    # -------------------------------------------------------------------------
    # Lookup helpers
    # -------------------------------------------------------------------------

    def _resolve_canonical_name(self, name_or_alias: str) -> str:
        """
        Resolve an input schema name or alias to its canonical schema name.
        """
        return self._aliases.get(name_or_alias, name_or_alias)

    def _load_config(self, canonical_name: str) -> Dict[str, Any]:
        """
        Load YAML config for a given canonical schema name.

        Conventional filename pattern: <lowercase schema name with no dashes>_mapping.yml
        Example: "ECLASS" -> "eclass_mapping.yml", "ISA-95" -> "isa95_mapping.yml"
        """
        if canonical_name in self._configs:
            return self._configs[canonical_name]

        file_stub = canonical_name.lower().replace("-", "")
        cfg_path = self.config_dir / f"{file_stub}_mapping.yml"

        if not cfg_path.exists():
            logger.debug(f"No config found for {canonical_name} at {cfg_path}, using empty config.")
            self._configs[canonical_name] = {}
            return self._configs[canonical_name]

        try:
            with cfg_path.open("r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                self._configs[canonical_name] = cfg
                logger.info(f"Loaded config for {canonical_name} from {cfg_path}")
        except Exception as exc:
            logger.warning(f"Failed to load config for {canonical_name} from {cfg_path}: {exc}")
            self._configs[canonical_name] = {}

        return self._configs[canonical_name]

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_mapper(self, name_or_alias: str, force_reload: bool = False) -> SchemaMapper:
        """
        Get an instantiated mapper for a given schema name or alias.

        Args:
            name_or_alias: The schema name or alias.
            force_reload: If True, create a new instance even if one is cached.

        Raises:
            KeyError if schema is not registered.
        """
        canonical = self._resolve_canonical_name(name_or_alias)

        if canonical not in self._mappers:
            raise KeyError(f"Schema '{name_or_alias}' not registered. Available: {list(self._mappers.keys())}")

        if not force_reload and canonical in self._instances:
            return self._instances[canonical]

        mapper_class_or_loader = self._mappers[canonical]
        if callable(mapper_class_or_loader) and not isinstance(mapper_class_or_loader, type):
            mapper_class = mapper_class_or_loader()
        else:
            mapper_class = mapper_class_or_loader  # type: ignore

        config = self._load_config(canonical)
        mapper = mapper_class(config=config)
        self._instances[canonical] = mapper
        logger.info(f"Created new mapper instance for {canonical}: {mapper}")
        return mapper

    def list_schemas(self) -> List[str]:
        """
        Return canonical names of all registered schemas.
        """
        return list(self._mappers.keys())

    def list_aliases(self, canonical_name: str) -> List[str]:
        """
        List all aliases for a canonical schema name.
        """
        return [a for a, c in self._aliases.items() if c == canonical_name]

    def info(self, name_or_alias: str) -> Dict[str, Any]:
        """
        Return metadata for a given schema (name or alias).
        """
        try:
            mapper = self.get_mapper(name_or_alias)
            canonical = self._resolve_canonical_name(name_or_alias)
            return {
                "name": mapper.get_schema_name(),
                "version": mapper.get_schema_version(),
                "canonical_name": canonical,
                "aliases": self.list_aliases(canonical),
                "mapper_class": mapper.__class__.__name__,
            }
        except KeyError as exc:
            return {"error": str(exc)}

    # -------------------------------------------------------------------------
    # Mapping utilities (using all layers + part classes)
    # -------------------------------------------------------------------------

    def map_dpp(self, name_or_alias: str, dpp: DigitalProductPassport) -> Dict[str, Any]:
        """
        Map a full DigitalProductPassport to the requested schema.

        This uses all layers:
            - identity
            - structure (incl. all PartClass-based components)
            - lifecycle
            - risk
            - sustainability
            - provenance

        Returns:
            A schema-specific dict as returned by SchemaMapper.map_dpp().
        """
        mapper = self.get_mapper(name_or_alias)
        logger.debug(f"Mapping DPP using schema {mapper.get_schema_name()}")
        return mapper.map_dpp(dpp)

    def map_part(self, name_or_alias: str, part: PartClass) -> Dict[str, Any]:
        """
        Map a single PartClass instance to the requested schema representation.

        Returns:
            Dict[str, Any]: Schema-specific representation of the part.
        """
        mapper = self.get_mapper(name_or_alias)
        logger.debug(
            f"Mapping PartClass(id={part.part_id}, type={part.type}) "
            f"using schema {mapper.get_schema_name()}"
        )
        return mapper.map_part_class(part)

    def map_layers(
        self,
        name_or_alias: str,
        identity: IdentityLayer,
        structure: StructureLayer,
        lifecycle: LifecycleLayer,
        risk: RiskLayer,
        sustainability: SustainabilityLayer,
        provenance: ProvenanceLayer,
    ) -> Dict[str, Any]:
        """
        Map individual DPP layers to the requested schema, without wrapping them
        into a full DigitalProductPassport object.

        This can be useful if you’ve constructed layers independently.

        Returns:
            Dict[str, Any]: Schema-compliant representation of all layers.
        """
        mapper = self.get_mapper(name_or_alias)
        logger.debug(f"Mapping individual layers using schema {mapper.get_schema_name()}")

        mapped = {
            "schema": mapper.get_schema_name(),
            "schema_version": mapper.get_schema_version(),
            "@context": mapper.get_context(),
            "identity": mapper.map_identity_layer(identity),
            "structure": mapper.map_structure_layer(structure),
            "lifecycle": mapper.map_lifecycle_layer(lifecycle),
            "risk": mapper.map_risk_layer(risk),
            "sustainability": mapper.map_sustainability_layer(sustainability),
            "provenance": mapper.map_provenance_layer(provenance),
        }

        ok, errors = mapper.validate_mapping(mapped)
        if not ok:
            raise ValueError(f"Mapped layer data invalid for {mapper.get_schema_name()}: {errors}")

        return mapped

    def __repr__(self) -> str:
        return f"SchemaRegistry(schemas={self.list_schemas()})"


# -------------------------------------------------------------------------
# Global helpers
# -------------------------------------------------------------------------

_global_registry: Optional[SchemaRegistry] = None


def get_global_registry() -> SchemaRegistry:
    """
    Get (or create) a global SchemaRegistry instance.
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = SchemaRegistry()
    return _global_registry


def register_default_mappers() -> None:
    """
    Register built-in mappers (ECLASS, ISA-95, etc.) with the global registry.

    Call this once at package initialization (e.g. in nmis_dpp/__init__.py).
    """
    registry = get_global_registry()

    # Lazy registration of built-ins
    registry.register_lazy(
        canonical_name="ECLASS",
        module_path="nmis_dpp.mappers.eclass_mapper",
        class_name="ECLASSMapper",
        aliases=["eclass", "EC"],
    )

    registry.register_lazy(
        canonical_name="ISA-95",
        module_path="nmis_dpp.mappers.isa95_mapper",
        class_name="ISA95Mapper",
        aliases=["ISA95", "isa95", "IEC62264"],
    )

    logger.info("Default mappers registered in global SchemaRegistry")
