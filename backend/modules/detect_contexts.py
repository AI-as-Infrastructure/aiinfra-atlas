# This module detects the context of questions and refines the output based on that context. It is primarily used to limit answers to a single corpus but might also be used to provide additional guardrails or expert knowledge.

import logging

def detect_context_conditions(query: str) -> list:
    query_lower = query.lower()
    
    condition_map = {
        # General country keywords
        'australia': 'au',
        'australian': 'au',
        'new zealand': 'nz',
        'nz': 'nz',
        'united kingdom': 'uk',
        'british': 'uk',
        'uk': 'uk',
        # Indigenous New Zealand contexts
        #'māori': 'indigenous_nz',
        #'maori': 'indigenous_nz',
        #'aotearoa': 'indigenous_nz',
        # Indigenous Australian contexts 
        #'aboriginal': 'indigenous_au',
        #'first nations': 'indigenous_au'
    }
    
    detected = {code for keyword, code in condition_map.items() if keyword in query_lower}
    logging.debug(f"Detected conditions: {detected}")
    return list(detected)