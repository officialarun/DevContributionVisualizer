from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import analytics, commits, repositories
from .config import ROOT
from .db import SessionLocal
from .errors import AppError
from .ingestion import service


@asynccontextmanager
async def lifespan(_: FastAPI):
    with SessionLocal() as session:
        service.reset_stale_running(session)
    yield


app = FastAPI(title="Developer Contribution Visualizer", lifespan=lifespan)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


@app.exception_handler(AppError)
async def app_error(_: Request, exc: AppError):
    return _error(exc.status_code, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    msg = "; ".join(f"{'.'.join(map(str, e['loc'][1:]))}: {e['msg']}" for e in exc.errors())
    return _error(422, "validation_error", msg)


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException):
    return _error(exc.status_code, "http_error", str(exc.detail))


for r in (repositories.router, analytics.router, commits.router):
    app.include_router(r, prefix="/api")

# Serve the built frontend (if present) so production is a single process.
_dist = ROOT / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            return _error(404, "not_found", "Unknown API route")
        file = (_dist / path).resolve()
        if path and file.is_file() and _dist in file.parents:
            return FileResponse(file)
        return FileResponse(_dist / "index.html")
