from typing import Dict, List, Any
from app.engines.tabular.generator import generate_tabular
import random

def generate_relational(schema: Dict[str, List[str]], primary_key: str, foreign_key: str, num_rows: int) -> Dict[str, List[Dict[str, Any]]]:
    """Generates two related tables ensuring referential integrity."""
    tables = list(schema.keys())
    parent_table = tables[0]
    child_table = tables[1]
    
    # 1. Generate Parent Data
    parent_data = generate_tabular(schema[parent_table], num_rows)
    
    # 2. Extract Primary Keys
    valid_pks = [row[primary_key] for row in parent_data if primary_key in row]
    
    # 3. Generate Child Data
    child_data = generate_tabular(schema[child_table], num_rows * 2)
    
    # 4. Enforce Relational Integrity
    for row in child_data:
        if valid_pks:
            row[foreign_key] = random.choice(valid_pks)
            
    return {
        parent_table: parent_data,
        child_table: child_data
    }