import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.routers import auth, commands, devices, health, reminders, scenes, user, voice, weather
from app.utils.response import error_response


app = FastAPI(
    title=settings.app_name,
    description="《软件工程》课程大作业后端 API",
    version="0.1.0",
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "success" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response("ERROR", str(exc.detail)),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=error_response("INVALID_REQUEST", "请求参数校验失败", jsonable_encoder(exc.errors())),
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request, exc: StarletteHTTPException):
    code = "NOT_FOUND" if exc.status_code == 404 else "ERROR"
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(code, str(exc.detail)),
    )


app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(devices.router, prefix=settings.api_prefix)
app.include_router(commands.router, prefix=settings.api_prefix)
app.include_router(reminders.router, prefix=settings.api_prefix)
app.include_router(weather.router, prefix=settings.api_prefix)
app.include_router(scenes.router, prefix=settings.api_prefix)
app.include_router(voice.router, prefix=settings.api_prefix)
app.include_router(user.router, prefix=settings.api_prefix)


def _mount_static_frontend() -> None:
    static_dir = os.getenv("SMART_HOME_STATIC_DIR")
    if not static_dir:
        return

    frontend_dir = Path(static_dir).resolve()
    index_file = frontend_dir / "index.html"
    assets_dir = frontend_dir / "assets"
    if not index_file.is_file():
        return

    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        requested_file = (frontend_dir / full_path).resolve()
        if requested_file.is_file() and frontend_dir in requested_file.parents:
            return FileResponse(requested_file)
        return FileResponse(index_file)


_mount_static_frontend()
