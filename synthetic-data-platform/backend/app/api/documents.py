from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.engines.documents.generator import generate_invoice_pdf

router = APIRouter(prefix="/api/v1/documents", tags=["Document Engine"])

class InvoiceItem(BaseModel):
    name: str
    amount: float

class InvoiceRequest(BaseModel):
    name: str
    email: str
    items: List[InvoiceItem]
    total: float

@router.post("/generate")
async def create_document(request: InvoiceRequest):
    try:
        data = request.dict()
        filepath = generate_invoice_pdf(data)
        return {
            "status": "success", 
            "file_path": filepath, 
            "message": "PDF generated successfully."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))