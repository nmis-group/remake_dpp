"""
utils.py

Utility functions for Digital Product Passport packages.
Includes serialization helpers and validation routines for parts and passport layers.

Author: Anmol Kumar, NMIS
"""

import json
from dataclasses import asdict, is_dataclass
from typing import Any


def to_dict(obj: Any) -> dict:
    """
    Recursively converts a dataclass or nested dataclasses to a dictionary.

    Args:
        obj (Any): A dataclass instance or nested structure.

    Returns:
        dict: Dictionary representation suitable for serialization.
    """
    if is_dataclass(obj):
        return asdict(obj)
    elif isinstance(obj, list):
        return [to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    else:
        return obj


def to_json(obj: Any, indent: int = 2) -> str:
    """
    Serializes a dataclass (or list/dict thereof) as a formatted JSON string.

    Args:
        obj (Any): A serializable dataclass object (or list/dict).
        indent (int): Indentation level for JSON output.

    Returns:
        str: JSON-formatted string representing the object.
    """
    return json.dumps(to_dict(obj), indent=indent, default=str)


def validate_part_class(part) -> bool:
    """
    Basic validator for PartClass and its subclasses.

    Args:
        part: An instance of PartClass or subclass.

    Returns:
        bool: True if minimal fields are present, else False.
    """
    required_fields = ["part_id", "name", "type"]
    for field in required_fields:
        if not hasattr(part, field) or getattr(part, field) is None:
            return False
    return True

