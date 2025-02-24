from typing import Dict

def validate_query(query: Dict) -> bool:
    """
    Validate a query dictionary.
    """
    required_fields = ["name", "query", "gauges"]
    for field in required_fields:
        if field not in query:
            return False
    return True