from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from backend.api import routes, stats, video
from backend.services.job_manager import JobError, JobManager
from backend.services.video_service import VideoService

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_app(upload_dir: Path | None = None, frontend_dir: Path | None = None) -> FastAPI:
    manager = JobManager(upload_dir if upload_dir is not None else PROJECT_ROOT / "storage/uploads")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            await run_in_threadpool(manager.shutdown)

    app = FastAPI(title="Visitor Counter API", lifespan=lifespan)
    app.state.manager = manager
    app.state.video_service = VideoService(manager)

    @app.exception_handler(JobError)
    async def job_error(request: Request, exc: JobError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.include_router(routes.router)
    app.include_router(video.router)
    app.include_router(stats.router)

    frontend = frontend_dir if frontend_dir is not None else PROJECT_ROOT / "frontend"
    if (frontend / "index.html").is_file():
        # Mounted last so that static routing cannot shadow the API.
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    else:
        @app.get("/", response_class=HTMLResponse, include_in_schema=False)
        def placeholder():
            return '<html lang="ru"><meta charset="utf-8"><title>Visitor Counter</title>' \
                   '<h1>Visitor Counter API</h1><p>Frontend пока не установлен.</p>' \
                   '<a href="/docs">Документация API</a></html>'

    return app


app = create_app()
