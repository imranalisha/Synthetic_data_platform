from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.engines.relational.generator import generate_relational

router = APIRouter(prefix="/api/v1/relational", tags=["Relational Engine"])

class RelationalRequest(BaseModel):
    schema_definition: Dict[str, List[str]]
    primary_key: str
    foreign_key: str
    num_rows: int = 50

@router.post("/generate")
async def create_relational_data(request: RelationalRequest):
    try:
        data = generate_relational(
            request.schema_definition, 
            request.primary_key, 
            request.foreign_key, 
            request.num_rows
        )
        return {"data": data, "status": "integrity_verified"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))