from fastapi import APIRouter, File, Form, UploadFile

from ..core.errors import not_implemented
from ..schemas.ai import (SchemaInferenceRequest, SchemaInferenceResponse, TextSynthesisRequest,
                          TextSynthesisResponse)

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/infer-schema", response_model=SchemaInferenceResponse)
def infer_schema(req: SchemaInferenceRequest):
    raise not_implemented("Step 3")


@router.post("/infer-schema/upload", response_model=SchemaInferenceResponse)
async def infer_schema_upload(file: UploadFile = File(...), max_tables: int = Form(10),
                              include_edge_cases: bool = Form(True)):
    raise not_implemented("Step 3")


@router.post("/synthesize-text", response_model=TextSynthesisResponse)
def synthesize_text(req: TextSynthesisRequest):
    raise not_implemented("Step 3")