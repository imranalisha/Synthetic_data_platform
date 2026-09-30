from fastapi import HTTPException

def not_implemented(step: str) -> HTTPException:
    return HTTPException(status_code=501, detail=f"Endpoint contract is final; logic lands in {step}.")