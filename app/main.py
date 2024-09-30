
from fastapi import FastAPI
from app.api.v1.endpoints import example, aeroplane

import uvicorn

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8085",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(example.router, prefix="/api/v1", tags=["example"])
app.include_router(aeroplane.router, prefix="/api/v1", tags=["aeroplane"])

if __name__ == '__main__':
    uvicorn.run("main:app", host='0.0.0.0', port=8000, reload=True)
