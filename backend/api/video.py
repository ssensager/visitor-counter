import asyncio
import logging

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import StreamingResponse

from backend.schemas.responses import JobActionResponse, StartRequest, UploadResponse
from backend.services.job_manager import JobError

router = APIRouter(prefix="/api/video", tags=["video"])
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=UploadResponse)
def upload(request: Request, file: UploadFile):
    try:
        return request.app.state.manager.upload(file.filename, file.file)
    except OSError:
        logger.exception("Failed to store upload")
        raise JobError(500, "Не удалось сохранить видео") from None
    finally:
        file.file.close()


@router.post("/start/{job_id}", response_model=JobActionResponse)
def start(job_id: str, request: Request, body: StartRequest | None = None):
    request.app.state.video_service.start(job_id, body.line if body else None)
    return JobActionResponse(job_id=job_id, status="processing")


@router.post("/stop/{job_id}", response_model=JobActionResponse)
def stop(job_id: str, request: Request):
    request.app.state.video_service.stop(job_id)
    return JobActionResponse(job_id=job_id, status="stopped")


@router.get("/stream/{job_id}")
async def stream(job_id: str, request: Request):
    manager = request.app.state.manager
    initial, _, _, generation = manager.snapshot(job_id)
    if initial.status == "uploaded":
        raise JobError(409, "Сначала запустите обработку")

    async def frames():
        revision = -1
        while not await request.is_disconnected():
            stats, jpeg, latest, run = manager.snapshot(job_id)
            if run != generation:
                break
            if jpeg is not None and latest != revision:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                       + str(len(jpeg)).encode("ascii") + b"\r\n\r\n" + jpeg + b"\r\n")
            revision = latest
            if stats.status in {"completed", "stopped", "error"}:
                break
            await asyncio.sleep(0.05)
        yield b"--frame--\r\n"

    return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
