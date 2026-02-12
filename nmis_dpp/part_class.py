"""
part_class.py

Defines universal, domain-neutral part classes for the Digital Product Passport
system. These classes expose:

- Domain-friendly, strongly-typed attributes for core engineering semantics.
- Ontology-agnostic hooks to bind each part class to one or more external
  ontologies (e.g., ECLASS, ISA-95, or domain-specific schemas).

Author: Anmol Kumar, NMIS
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


# ---------------------------------------------------------------------------
# Ontology binding model (ontology-agnostic)
# ---------------------------------------------------------------------------

@dataclass
class OntologyBinding:
    """
    Ontology-agnostic description of how a part class maps into a given ontology.

    This structure is intentionally generic so it can accommodate ECLASS,
    ISA-95, and any other domain ontology.

    Attributes:
        ontology_name:
            Human-readable or code name of the ontology
            (e.g., "ECLASS", "ISA-95", "MyCompanySchema").

        class_ids:
            List of ontology class identifiers that correspond to this
            PartClass category. For ECLASS, these could be class IRDIs or
            hierarchy codes; for ISA-95, equipment class identifiers, etc.

        case_item_ids:
            List of ontology item identifiers that are declared as
            "case-of" these class_ids (or equivalent relation).
            For ECLASS, these are item classes with iscaseof/classref
            pointing to one of class_ids.

        metadata:
            Free-form dictionary for additional ontology-specific details,
            such as:
              - per-property IRDIs, units, and mappings
              - labels in different languages
              - hierarchy relationships (parent/child classes)
              - any other schema-specific annotations
    """
    ontology_name: str
    class_ids: List[str] = field(default_factory=list)
    case_item_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Base part model
# ---------------------------------------------------------------------------

@dataclass
class PartClass:
    """
    Base class for all part types.

    This represents a single part instance in the DPP, with optional
    bindings to multiple external ontologies.

    Attributes:
        part_id:
            Unique identifier for the part instance within the DPP.

        name:
            Descriptive name of the part instance (e.g., "Main Gearbox").

        type:
            The category of the part (e.g., 'Sensor', 'Actuator',
            'PowerConversion'). Typically set to the class name or a
            canonical label.

        properties:
            Flexible, additional properties not covered by the strongly-
            typed fields in subclasses. Keys should be meaningful strings,
            values can be any JSON-serializable type.

        ontology_bindings:
            Mapping from ontology name to OntologyBinding. This allows a
            single PartClass instance to be mapped into multiple ontologies
            without changing its core engineering semantics.
    """
    part_id: str
    name: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    ontology_bindings: Dict[str, OntologyBinding] = field(default_factory=dict)

    # ---------------------------
    # Ontology-related helpers
    # ---------------------------

    def bind_ontology(
        self,
        ontology_name: str,
        class_ids: Optional[List[str]] = None,
        case_item_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Attach or update an ontology binding for this part.

        Typical usage (from a mapper or registry):
            part.bind_ontology(
                "ECLASS",
                class_ids=["0173-101-AGW606007"],
                case_item_ids=["0173-102-..."],
                metadata={...}
            )

        Args:
            ontology_name:
                Name of the ontology (e.g., "ECLASS", "ISA-95").

            class_ids:
                List of ontology class identifiers corresponding to this
                PartClass; empty or None if not applicable.

            case_item_ids:
                List of ontology item-class identifiers that are declared
                as case-of this class (or equivalent relation).

            metadata:
                Optional free-form ontology-specific metadata. If a binding
                already exists, its metadata will be updated/merged.
        """
        existing = self.ontology_bindings.get(ontology_name)

        if existing is None:
            binding = OntologyBinding(
                ontology_name=ontology_name,
                class_ids=class_ids or [],
                case_item_ids=case_item_ids or [],
                metadata=metadata or {},
            )
            self.ontology_bindings[ontology_name] = binding
        else:
            if class_ids is not None:
                # Merge while avoiding duplicates
                existing.class_ids = list(
                    { *existing.class_ids, *class_ids }
                )
            if case_item_ids is not None:
                existing.case_item_ids = list(
                    { *existing.case_item_ids, *case_item_ids }
                )
            if metadata:
                existing.metadata.update(metadata)

    def get_binding(self, ontology_name: str) -> Optional[OntologyBinding]:
        """
        Retrieve the OntologyBinding for a given ontology, if present.

        Args:
            ontology_name: Name of the ontology.

        Returns:
            OntologyBinding if bound, else None.
        """
        return self.ontology_bindings.get(ontology_name)

    def allowed_item_types(self, ontology_name: str) -> List[str]:
        """
        Return a list of ontology item types (case classes) that this
        PartClass can manifest as in the given ontology.

        For example, when using ECLASS:
            - class_ids could be ECLASS categorization classes.
            - case_item_ids are item classes that have iscaseof/classref
              pointing to those classes.

        Args:
            ontology_name: Name of the ontology.

        Returns:
            List of ontology item identifiers; empty if no binding exists.
        """
        binding = self.get_binding(ontology_name)
        if not binding:
            return []
        return list(binding.case_item_ids)

    def supported_ontologies(self) -> List[str]:
        """
        Return a list of ontology names for which this part currently
        has bindings.

        Returns:
            List of ontology names (e.g., ["ECLASS", "ISA-95"]).
        """
        return list(self.ontology_bindings.keys())


# ---------------------------------------------------------------------------
# Domain-specific subclasses
# ---------------------------------------------------------------------------

@dataclass
class PowerConversion(PartClass):
    """
    Represents power conversion devices (e.g., PSUs, inverters, alternators).

    Attributes:
        input_voltage:
            Nominal input voltage in volts.

        output_voltage:
            Nominal output voltage in volts.

        power_rating:
            Maximum continuous output power in watts.

        efficiency:
            Efficiency as a fraction between 0 and 1 (e.g., 0.92).
    """
    input_voltage: Optional[float] = None
    output_voltage: Optional[float] = None
    power_rating: Optional[float] = None
    efficiency: Optional[float] = None


@dataclass
class EnergyStorage(PartClass):
    """
    Represents energy storage devices (e.g., batteries, capacitors).

    Attributes:
        capacity:
            Storage capacity in Wh for batteries or F for capacitors.

        voltage:
            Nominal voltage in volts.

        chemistry:
            Type of chemistry or dielectric (e.g., "Li-ion", "NiMH").

        recharge_cycles:
            Typical number of recharge cycles supported.
    """
    capacity: Optional[float] = None
    voltage: Optional[float] = None
    chemistry: Optional[str] = None
    recharge_cycles: Optional[int] = None


@dataclass
class Actuator(PartClass):
    """
    Represents actuators (e.g., motors, valves, servos).

    Attributes:
        torque:
            Maximum torque in newton-metres (Nm).

        speed:
            Maximum speed in revolutions per minute (rpm).

        duty_cycle:
            Recommended duty cycle as a fraction (0-1) or percentage.

        voltage:
            Operating voltage in volts.

        actuation_type:
            Type of actuation (e.g., "electric", "hydraulic", "pneumatic").
    """
    torque: Optional[float] = None
    speed: Optional[float] = None
    duty_cycle: Optional[float] = None
    voltage: Optional[float] = None
    actuation_type: Optional[str] = None


@dataclass
class Sensor(PartClass):
    """
    Represents sensors (e.g., temperature, pressure, flow, vibration, IMU).

    Attributes:
        sensor_type:
            Type of sensor (e.g., "temperature", "pressure", "IMU").

        range_min:
            Minimum measurable value.

        range_max:
            Maximum measurable value.

        accuracy:
            Sensor accuracy as a percentage or absolute units.

        drift:
            Expected measurement drift per unit time.

        response_time:
            Response time in milliseconds.
    """
    sensor_type: Optional[str] = None
    range_min: Optional[float] = None
    range_max: Optional[float] = None
    accuracy: Optional[float] = None
    drift: Optional[float] = None
    response_time: Optional[float] = None


@dataclass
class ControlUnit(PartClass):
    """
    Represents control units (e.g., ECU, MCU boards, FADEC).

    Attributes:
        cpu_type:
            Core or processor type (e.g., "ARM Cortex-M4").

        memory:
            RAM size in megabytes.

        firmware_version:
            Installed firmware version identifier.

        io_count:
            Number of input/output channels.
    """
    cpu_type: Optional[str] = None
    memory: Optional[float] = None
    firmware_version: Optional[str] = None
    io_count: Optional[int] = None


@dataclass
class UserInterface(PartClass):
    """
    Represents user interface devices (e.g., HMI, buttons, touchscreens, indicators).

    Attributes:
        ui_type:
            UI type (e.g., "touchscreen", "button panel").

        display_size:
            Size of display (inches), if applicable.

        input_methods:
            Supported input methods (e.g., ["touch", "button", "dial"]).

        indicator_count:
            Number of indicators/LEDs.
    """
    ui_type: Optional[str] = None
    display_size: Optional[float] = None
    input_methods: Optional[List[str]] = None
    indicator_count: Optional[int] = None


@dataclass
class Thermal(PartClass):
    """
    Represents thermal devices (e.g., heaters, exchangers, fans).

    Attributes:
        power:
            Thermal or electrical power in watts.

        delta_t:
            Maximum temperature difference managed (Kelvin or °C).

        airflow:
            Maximum airflow (e.g., CFM or L/min).
    """
    power: Optional[float] = None
    delta_t: Optional[float] = None
    airflow: Optional[float] = None


@dataclass
class Fluidics(PartClass):
    """
    Represents fluidic devices (e.g., pumps, tanks, lines, filters).

    Attributes:
        flow_rate:
            Maximum flow rate (e.g., L/min).

        pressure:
            Maximum pressure (e.g., bar, psi).

        fluid_type:
            Compatible fluids (e.g., "water", "hydraulic oil").

        volume:
            Internal volume (for tanks) in litres.
    """
    flow_rate: Optional[float] = None
    pressure: Optional[float] = None
    fluid_type: Optional[str] = None
    volume: Optional[float] = None


@dataclass
class Structural(PartClass):
    """
    Represents structural elements (e.g., housings, frames, blades, disks).

    Attributes:
        material:
            Primary material (e.g., "aluminium alloy", "titanium").

        mass:
            Component mass in kilograms.

        dimensions:
            Dictionary of named dimensions (e.g., {"length": 100.0, "width": 50.0}).

        load_rating:
            Maximum load or stress (e.g., N, N·m, MPa).
    """
    material: Optional[str] = None
    mass: Optional[float] = None
    dimensions: Optional[Dict[str, float]] = None
    load_rating: Optional[float] = None


@dataclass
class Transmission(PartClass):
    """
    Represents transmission components (e.g., gears, bearings, belts, shafts).

    Attributes:
        torque_rating:
            Maximum torque supported in newton-metres (Nm).

        speed_rating:
            Maximum speed supported in revolutions per minute (rpm).

        transmission_type:
            Transmission type (e.g., "gear", "belt", "shaft", "chain").
    """
    torque_rating: Optional[float] = None
    speed_rating: Optional[float] = None
    transmission_type: Optional[str] = None


@dataclass
class Protection(PartClass):
    """
    Represents protection devices (e.g., fuses, breakers, EMI/RFI filters).

    Attributes:
        protection_type:
            Type of protection (e.g., "fuse", "breaker", "filter").

        rating:
            Protection rating (e.g., current in A, voltage in V).

        response_time:
            Trip/response time in milliseconds.
    """
    protection_type: Optional[str] = None
    rating: Optional[float] = None
    response_time: Optional[float] = None


@dataclass
class Connectivity(PartClass):
    """
    Represents connectivity components (e.g., harnesses, connectors, buses).

    Attributes:
        interface_type:
            Interface type (e.g., "power", "Ethernet", "CAN").

        connector_standard:
            Reference standard (e.g., "USB-C", "RJ45").

        pin_count:
            Number of electrical pins or equivalent connectors.
    """
    interface_type: Optional[str] = None
    connector_standard: Optional[str] = None
    pin_count: Optional[int] = None


@dataclass
class SoftwareModule(PartClass):
    """
    Represents software elements (e.g., firmware, control laws, DSP blocks).

    Attributes:
        version:
            Software module version identifier.

        language:
            Implementation language (e.g., "C", "C++", "Python").

        license:
            License identifier (e.g., "MIT", "GPL-3.0").

        checksums:
            Dictionary of checksums or hashes keyed by algorithm name
            (e.g., {"sha256": "..."}).
    """
    version: Optional[str] = None
    language: Optional[str] = None
    license: Optional[str] = None
    checksums: Optional[Dict[str, str]] = None


@dataclass
class Consumable(PartClass):
    """
    Represents consumable elements (e.g., filters, seals, oils).

    Attributes:
        consumable_type:
            Consumable product type (e.g., "filter", "oil", "seal").

        capacity:
            Capacity or quantity (e.g., litres, grams).

        replacement_interval:
            Suggested replacement interval (e.g., "500 h", "12 months").
    """
    consumable_type: Optional[str] = None
    capacity: Optional[float] = None
    replacement_interval: Optional[str] = None


@dataclass
class Fastener(PartClass):
    """
    Represents fastening elements (e.g., screws, rivets, adhesives).

    Attributes:
        fastener_type:
            Kind of fastener (e.g., "screw", "bolt", "adhesive").

        material:
            Material of the fastener (e.g., "steel", "aluminium").

        diameter:
            Diameter in millimetres.

        length:
            Length in millimetres.

        strength:
            Tensile or shear strength (e.g., N, MPa).
    """
    fastener_type: Optional[str] = None
    material: Optional[str] = None
    diameter: Optional[float] = None
    length: Optional[float] = None
    strength: Optional[float] = None
