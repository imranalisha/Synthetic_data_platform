from faker import Faker
from typing import List, Dict, Any
import uuid

fake = Faker()

def generate_tabular(columns: List[str], num_rows: int) -> List[Dict[str, Any]]:
    """Generates tabular data based on column name heuristics."""
    dataset = []
    for _ in range(num_rows):
        row = {}
        for col in columns:
            col_lower = col.lower()
            if "id" in col_lower:
                row[col] = str(uuid.uuid4())
            elif "name" in col_lower:
                row[col] = fake.name()
            elif "email" in col_lower:
                row[col] = fake.email()
            elif "phone" in col_lower:
                row[col] = fake.phone_number()
            elif "address" in col_lower:
                row[col] = fake.address().replace('\n', ', ')
            elif "date" in col_lower:
                row[col] = fake.date_this_decade().isoformat()
            elif "amount" in col_lower or "price" in col_lower:
                row[col] = round(fake.random.uniform(10.0, 5000.0), 2)
            else:
                row[col] = fake.word()
        dataset.append(row)
    return dataset