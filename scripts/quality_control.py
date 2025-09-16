"""Quality control system for AI agent outputs."""

import json
import re
from typing import Any, Dict, List, Optional, Tuple
import logging
from storage import FileStorage

logger = logging.getLogger(__name__)

# Initialize storage
storage = FileStorage()

class QualityControl:
    """Manages automated quality checks and validation for agent outputs."""
    
    @staticmethod
    def validate_output(
        output: Any,
        task_type: str,
        validation_rules: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str]]:
        """Validate agent output against defined rules."""
        issues = []
        
        if validation_rules is None:
            validation_rules = QualityControl.get_validation_rules(task_type)
        
        # Type validation
        expected_type = validation_rules.get('type')
        if expected_type and not isinstance(output, eval(expected_type)):
            issues.append(f"Invalid output type. Expected {expected_type}, got {type(output)}")
        
        # Schema validation
        if schema := validation_rules.get('schema'):
            issues.extend(QualityControl._validate_schema(output, schema))
        
        # Content validation
        if content_rules := validation_rules.get('content'):
            issues.extend(QualityControl._validate_content(output, content_rules))
        
        # Size validation
        if size_rules := validation_rules.get('size'):
            issues.extend(QualityControl._validate_size(output, size_rules))
        
        return len(issues) == 0, issues
    
    @staticmethod
    def _validate_schema(data: Any, schema: Dict[str, Any]) -> List[str]:
        """Validate data structure against a schema."""
        issues = []
        
        if not isinstance(data, dict):
            return ["Data must be a dictionary"]
        
        for field, rules in schema.items():
            if field not in data:
                if rules.get('required', False):
                    issues.append(f"Missing required field: {field}")
                continue
            
            value = data[field]
            field_type = rules.get('type')
            
            if field_type and not isinstance(value, eval(field_type)):
                issues.append(f"Invalid type for {field}: expected {field_type}")
            
            if pattern := rules.get('pattern'):
                if not re.match(pattern, str(value)):
                    issues.append(f"Invalid format for {field}")
            
            if enum := rules.get('enum'):
                if value not in enum:
                    issues.append(f"Invalid value for {field}: must be one of {enum}")
        
        return issues
    
    @staticmethod
    def _validate_content(data: Any, rules: Dict[str, Any]) -> List[str]:
        """Validate content against defined rules."""
        issues = []
        
        content = str(data)
        
        if min_length := rules.get('min_length'):
            if len(content) < min_length:
                issues.append(f"Content too short: {len(content)} < {min_length}")
        
        if max_length := rules.get('max_length'):
            if len(content) > max_length:
                issues.append(f"Content too long: {len(content)} > {max_length}")
        
        if banned_patterns := rules.get('banned_patterns'):
            for pattern in banned_patterns:
                if re.search(pattern, content):
                    issues.append(f"Contains banned pattern: {pattern}")
        
        if required_patterns := rules.get('required_patterns'):
            for pattern in required_patterns:
                if not re.search(pattern, content):
                    issues.append(f"Missing required pattern: {pattern}")
        
        return issues
    
    @staticmethod
    def _validate_size(data: Any, rules: Dict[str, Any]) -> List[str]:
        """Validate size constraints."""
        issues = []
        
        if isinstance(data, (list, dict)):
            size = len(data)
            if min_size := rules.get('min_size'):
                if size < min_size:
                    issues.append(f"Too few items: {size} < {min_size}")
            if max_size := rules.get('max_size'):
                if size > max_size:
                    issues.append(f"Too many items: {size} > {max_size}")
        
        if isinstance(data, str):
            size = len(data.encode('utf-8'))
            if max_bytes := rules.get('max_bytes'):
                if size > max_bytes:
                    issues.append(f"Data too large: {size} > {max_bytes} bytes")
        
        return issues
    
    @staticmethod
    def get_validation_rules(task_type: str) -> Dict[str, Any]:
        """Get validation rules for a task type."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT validation_rules
                    FROM task_validation_rules
                    WHERE task_type = %s
                """, (task_type,))
                result = cur.fetchone()
                
                if result:
                    return result[0]
                
                # Return default rules if none found
                return {
                    'type': 'dict',
                    'schema': {
                        'status': {
                            'type': 'str',
                            'required': True,
                            'enum': ['success', 'error']
                        },
                        'message': {
                            'type': 'str',
                            'required': True
                        }
                    },
                    'content': {
                        'min_length': 1,
                        'max_length': 1000000,
                        'banned_patterns': [
                            r'password\s*=',
                            r'api_key\s*=',
                            r'secret\s*='
                        ]
                    },
                    'size': {
                        'max_bytes': 5000000  # 5MB
                    }
                }
    
    @staticmethod
    def record_validation_result(
        task_id: str,
        passed: bool,
        issues: List[str]
    ) -> None:
        """Record validation results for a task."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO task_validations (
                        task_id,
                        passed,
                        issues
                    ) VALUES (%s, %s, %s)
                """, (task_id, passed, json.dumps(issues)))
                conn.commit()