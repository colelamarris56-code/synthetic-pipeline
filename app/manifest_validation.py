"""
JSON Schema validation for clinic synthesis manifests.
Provides validation functions and schema definitions for manifest validation.
"""
from typing import Any, Optional
from jsonschema import validate, ValidationError

# Schema for individual patient record requirements
PATIENT_SCHEMA = {
    "type": "object",
    "properties": {
        "age_range": {
            "type": "object",
            "properties": {
                "min": {"type": "integer", "minimum": 0},
                "max": {"type": "integer", "minimum": 0}
            },
            "required": ["min", "max"]
        },
        "conditions": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1
        },
        "medications": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["age_range", "conditions"]
}

# Schema for the complete synthesis manifest
MANIFEST_SCHEMA = {
    "type": "object",
    "properties": {
        "clinic_name": {"type": "string"},
        "record_count": {"type": "integer", "minimum": 1},
        "patient_requirements": {
            "type": "array",
            "items": PATIENT_SCHEMA,
            "minItems": 1
        },
        "output_format": {
            "type": "string",
            "enum": ["csv", "json", "parquet"]
        }
    },
    "required": ["clinic_name", "record_count", "patient_requirements", "output_format"]
}

class ManifestValidationError(Exception):
    """Exception raised for manifest validation errors."""
    def __init__(self, message: str, validation_errors: Optional[list[str]] = None):
        super().__init__(message)
        self.validation_errors = validation_errors or []

def validate_manifest(manifest: dict[str, Any]) -> None:
    """
    Validate a synthesis manifest against the schema.
    
    Args:
        manifest: The manifest to validate
        
    Raises:
        ManifestValidationError: If validation fails
    """
    try:
        validate(manifest, MANIFEST_SCHEMA)
        
        # Additional validation logic
        for req in manifest["patient_requirements"]:
            age_range = req["age_range"]
            if age_range["min"] > age_range["max"]:
                raise ManifestValidationError(
                    "Invalid age range",
                    [f"Minimum age {age_range['min']} is greater than maximum age {age_range['max']}"]
                )
            
    except ValidationError as e:
        raise ManifestValidationError(
            "Manifest validation failed",
            [e.message]
        )