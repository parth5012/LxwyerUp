import re
from typing import Dict, Any

class GuardrailsException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

def validate_user_input(text: str) -> Dict[str, Any]:
    """
    Validates user prompt for SQL injection patterns, prompt injection attempts,
    or malicious/abusive text.
    """
    if not text or len(text.strip()) == 0:
        return {"is_safe": False, "reason": "Empty input"}

    if len(text) > 4000:
        return {"is_safe": False, "reason": "Input exceeds character limit of 4000"}

    # Prompt injection patterns
    injection_patterns = [
        r"(ignore|disregard|bypass|overwrite)\b.*\b(previous|system|prompt|instructions)",
        r"you are now a",
        r"act as",
        r"ignore all rules",
    ]

    for pattern in injection_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return {"is_safe": False, "reason": "Potential prompt injection attempt detected."}

    # SQL Injection simple patterns
    sql_patterns = [
        r"UNION\s+SELECT",
        r"SELECT\s+.*\s+FROM",
        r"DROP\s+TABLE",
        r"INSERT\s+INTO",
    ]

    for pattern in sql_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return {"is_safe": False, "reason": "Security block: Disallowed query constructs."}

    return {"is_safe": True, "reason": None}
