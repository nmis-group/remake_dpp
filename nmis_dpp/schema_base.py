"""
schema_base.py

Abstract base class for all schema mappers.

All schema-specific mappers (e.g. ECLASS, ISA-95/IEC 62264) must inherit from
SchemaMapper and implement the required abstract methods for mapping each
Digital Product Passport (DPP) layer and for validation.

This design enables a plug-in architecture for different schemas:
new schemas can be added without changing the core mapping logic – only a
new mapper subclass and (optionally) a new YAML config are needed.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from typing import Dict, Any, Optional, List, Tuple
import logging

from nmis_dpp.model import (
    DigitalProductPassport,
    IdentityLayer,
    StructureLayer,
    LifecycleLayer,
    RiskLayer,
    SustainabilityLayer,
    ProvenanceLayer,
)
from nmis_dpp.part_class import PartClass


logger = logging.getLogger(__name__)


class SchemaMapper(ABC):
    """
    Abstract base class for mapping Digital Product Passport (DPP) objects
    to various external ontologies/standards (e.g. ECLASS, ISA-95).

    Subclasses must implement (at minimum):

        - get_schema_name():
              Return a short identifier for this schema
              (e.g., "ECLASS", "ISA-95").

        - get_schema_version():
              Return the schema/release version
              (e.g., "12.0", "2.0").

        - map_identity_layer():
              Map IdentityLayer to the target schema representation.

        - map_structure_layer():
              Map StructureLayer (including all part classes) to the schema.

        - map_lifecycle_layer():
              Map LifecycleLayer to the schema.

        - map_risk_layer():
              Map RiskLayer to the schema.

        - map_sustainability_layer():
              Map SustainabilityLayer to the schema.

        - map_provenance_layer():
              Map ProvenanceLayer to the schema.

        - validate_mapping():
              Check that mapped data satisfies minimal schema constraints.

        - get_context():
              Return a JSON-LD @context for this schema, enabling
              semantic/linked-data export.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the mapper with an optional configuration.

        Args:
            config:
                Configuration dictionary for the mapper, typically loaded from
                a YAML or JSON file (e.g. mapping tables, IRDIs, required fields).
                If None, an empty dict is used.
        """
        self.config: Dict[str, Any] = config or {}
        logger.info("Initialized %s mapper.", self.get_schema_name())

    # -------------------------------------------------------------------------
    # Schema metadata
    # -------------------------------------------------------------------------

    @abstractmethod
    def get_schema_name(self) -> str:
        """
        Return the canonical name of the schema this mapper targets.

        Returns:
            str: Schema name (e.g., "ECLASS", "ISA-95").
        """
        raise NotImplementedError

    @abstractmethod
    def get_schema_version(self) -> str:
        """
        Return the version/release of the schema.

        Returns:
            str: Schema version string (e.g., "12.0", "2.0.0").
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Layer mapping methods
    # -------------------------------------------------------------------------

    @abstractmethod
    def map_identity_layer(self, layer: IdentityLayer) -> Dict[str, Any]:
        """
        Map the IdentityLayer to a schema-specific representation.

        Args:
            layer: IdentityLayer instance from the DPP.

        Returns:
            Dict[str, Any]: Schema-compliant identity data.
        """
        raise NotImplementedError

    @abstractmethod
    def map_structure_layer(self, layer: StructureLayer) -> Dict[str, Any]:
        """
        Map the StructureLayer to a schema-specific representation.

        This layer typically includes the product/subsystem/assembly/component
        hierarchy as well as the included PartClass instances.

        Args:
            layer: StructureLayer instance from the DPP.

        Returns:
            Dict[str, Any]: Schema-compliant structure data.
        """
        raise NotImplementedError

    @abstractmethod
    def map_lifecycle_layer(self, layer: LifecycleLayer) -> Dict[str, Any]:
        """
        Map the LifecycleLayer to a schema-specific representation.

        This layer may include manufacturing batches, usage counters,
        maintenance/service information, and end-of-life data.

        Args:
            layer: LifecycleLayer instance from the DPP.

        Returns:
            Dict[str, Any]: Schema-compliant lifecycle data.
        """
        raise NotImplementedError

    @abstractmethod
    def map_risk_layer(self, layer: RiskLayer) -> Dict[str, Any]:
        """
        Map the RiskLayer to a schema-specific representation.

        This may include safety/mission criticality, FMEA entries,
        vulnerability information, etc.

        Args:
            layer: RiskLayer instance from the DPP.

        Returns:
            Dict[str, Any]: Schema-compliant risk data.
        """
        raise NotImplementedError

    @abstractmethod
    def map_sustainability_layer(self, layer: SustainabilityLayer) -> Dict[str, Any]:
        """
        Map the SustainabilityLayer to a schema-specific representation.

        This layer typically includes mass/energy, recycled content,
        remanufacturability, and related KPIs.

        Args:
            layer: SustainabilityLayer instance from the DPP.

        Returns:
            Dict[str, Any]: Schema-compliant sustainability data.
        """
        raise NotImplementedError

    @abstractmethod
    def map_provenance_layer(self, layer: ProvenanceLayer) -> Dict[str, Any]:
        """
        Map the ProvenanceLayer to a schema-specific representation.

        This can include digital signatures, certificates,
        and traceability links to events or external systems.

        Args:
            layer: ProvenanceLayer instance from the DPP.

        Returns:
            Dict[str, Any]: Schema-compliant provenance data.
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Validation and context
    # -------------------------------------------------------------------------

    @abstractmethod
    def validate_mapping(self, mapped_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate that mapped data conforms to schema requirements and constraints.

        Args:
            mapped_data:
                The complete mapped representation (typically as returned
                by map_dpp()).

        Returns:
            Tuple[bool, List[str]]:
                (is_valid, list_of_error_messages).

                - If valid:   (True, [])
                - If invalid: (False, ["error1", "error2", ...])
        """
        raise NotImplementedError

    @abstractmethod
    def get_context(self) -> Dict[str, Any]:
        """
        Return JSON-LD @context definition for this schema.

        The context maps short property names to IRIs/URIs used in Linked Data,
        enabling JSON-LD export of the mapped DPP.

        Returns:
            Dict[str, Any]:
                JSON-LD context, e.g.:

                    {
                        "@context": {
                            "schema": "http://schema.org/",
                            "identifier": "schema:identifier",
                            ...
                        }
                    }
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # High-level mapping entry points
    # -------------------------------------------------------------------------

    def map_dpp(self, dpp: DigitalProductPassport) -> Dict[str, Any]:
        """
        Map an entire DigitalProductPassport into the target schema.

        This is the main high-level entry point for consumers. It calls all
        layer-specific mapping methods and aggregates their results into a
        single schema-specific document, then validates it.

        Args:
            dpp:
                The DigitalProductPassport object to map.

        Returns:
            Dict[str, Any]:
                Complete schema-compliant representation.

        Raises:
            ValueError:
                If validation fails (validate_mapping() returns is_valid=False).
            Exception:
                Any error raised during mapping is logged and re-raised.
        """
        try:
            logger.info("Starting mapping to %s ...", self.get_schema_name())

            mapped: Dict[str, Any] = {
                "schema": self.get_schema_name(),
                "schema_version": self.get_schema_version(),
                "@context": self.get_context(),
                "identity": self.map_identity_layer(dpp.identity),
                "structure": self.map_structure_layer(dpp.structure),
                "lifecycle": self.map_lifecycle_layer(dpp.lifecycle),
                "risk": self.map_risk_layer(dpp.risk),
                "sustainability": self.map_sustainability_layer(dpp.sustainability),
                "provenance": self.map_provenance_layer(dpp.provenance),
            }

            # Validate mapped data for the target schema
            is_valid, errors = self.validate_mapping(mapped)
            if not is_valid:
                error_msg = f"Validation failed: {'; '.join(errors)}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.info("Successfully mapped DPP to %s.", self.get_schema_name())
            return mapped

        except Exception as exc:
            logger.error("Error during mapping to %s: %s", self.get_schema_name(), exc)
            raise

    def map_part_class(self, part: PartClass) -> Dict[str, Any]:
        """
        Map a single PartClass instance into the target schema representation.

        Subclasses can override this method to provide custom mapping logic
        (for example, applying ECLASS codes, IRDIs, or ISA-95 equipment types).

        By default, this simply converts the PartClass dataclass to a dict.

        Args:
            part:
                The PartClass instance to map.

        Returns:
            Dict[str, Any]: Schema-compliant representation of the part.
        """
        return asdict(part)

    # -------------------------------------------------------------------------
    # Config access helper
    # -------------------------------------------------------------------------

    def get_mapping_config(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a configuration value specific to this mapper.

        Typically used to access mapping tables, default values, or
        schema-specific flags loaded from an external YAML/JSON file.

        Args:
            key:
                Configuration key (e.g., "part_class_mapping", "layer_mapping").
            default:
                Value to return if key is not present in self.config.

        Returns:
            Any: The configuration value for the given key, or default.
        """
        return self.config.get(key, default)

    # -------------------------------------------------------------------------
    # Introspection
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """
        Human-readable representation of the mapper instance, including
        schema name and version.
        """
        return (
            f"{self.__class__.__name__}"
            f"(schema={self.get_schema_name()}, version={self.get_schema_version()})"
        )
