from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.engines.tabular.generator import generate_tabular

router = APIRouter(prefix="/api/v1/tabular", tags=["Tabular Engine"])

class TabularRequest(BaseModel):
    columns: List[str]
    num_rows: int = 100

class TabularResponse(BaseModel):
    data: List[Dict[str, Any]]
    total_generated: int

@router.post("/generate", response_model=TabularResponse)
async def create_tabular_data(request: TabularRequest):
    try:
        data = generate_tabular(request.columns, request.num_rows)
        return {"data": data, "total_generated": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))