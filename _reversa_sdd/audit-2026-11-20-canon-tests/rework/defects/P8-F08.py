"""P8-F08 reproduction: an unexpected kernel exception leaves POST /canon/compute without the error envelope.

Run:  cd <frozen copy> && PY <this file>
The real FastAPI application with an in-memory database (as app/tests/test_canon_endpoint.py does);
only the kernel facade is replaced by one that raises. Changes nothing on disk.
"""

import logging
import sys
from collections.abc import Iterator
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app as app_package
from app.db.base import Base
from app.db.session import get_db
from app.main import app as application
from app.services import canon_service

logging.disable(logging.CRITICAL)
print("app imported from:", Path(app_package.__file__).parent)
print("exception handlers registered:", sorted(
    getattr(k, "__name__", str(k)) for k in application.exception_handlers))

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(bind=engine)
factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def in_memory_db() -> Iterator[Session]:
    with factory() as db:
        yield db
        db.commit()


application.dependency_overrides[get_db] = in_memory_db
client = TestClient(application, raise_server_exceptions=False)  # answer as the server would


def show(label: str, response) -> None:
    print(f"\n[{label}]")
    print("  status      :", response.status_code)
    print("  content-type:", response.headers.get("content-type"))
    print("  body        :", response.text[:300])
    try:
        body = response.json()
        print("  envelope    :", isinstance(body, dict) and set(body) == {"error"})
    except ValueError:
        print("  envelope    : no (the body is not JSON)")


async def broken(aircraft, request, **_limits):
    raise RuntimeError("boom /private/var/x")


canon_service.KERNEL = type("Facade", (), {"compute": staticmethod(broken)})()
BODY = {"aircraft": {"fleet": "bryan"}, "quantities": ["stall-speed"]}
show("A  kernel raises RuntimeError (not a ServiceException)", client.post("/canon/compute", json=BODY))
show("A' control: unknown aircraft (NotFoundError, a ServiceException)",
     client.post("/canon/compute", json={**BODY, "aircraft": {"fleet": "nonexistent"}}))
show("A'' control: request validation error", client.post("/canon/compute", json={"quantities": 3}))
