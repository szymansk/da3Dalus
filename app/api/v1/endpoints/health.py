import http

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/health")
def read_hello():
    return JSONResponse(
        status_code=http.HTTPStatus.CREATED,
        content={"message": "Healthy"}
    )