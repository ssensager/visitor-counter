import asyncio
from contextlib import suppress

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from backend.schemas.responses import StatsResponse
from backend.services.job_manager import JobError

router = APIRouter(tags=["stats"])


@router.get("/api/stats/{job_id}", response_model=StatsResponse)
def stats(job_id: str, request: Request):
    return request.app.state.manager.snapshot(job_id)[0]


@router.websocket("/ws/stats/{job_id}")
async def websocket_stats(websocket: WebSocket, job_id: str):
    manager = websocket.app.state.manager
    await websocket.accept()
    try:
        manager.snapshot(job_id)
    except JobError as exc:
        await websocket.send_json({"detail": exc.detail})
        await websocket.close(code=1008)
        return

    async def disconnected():
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return

    async def updates():
        revision = -1
        generation = None
        while True:
            value, _, latest, run = manager.snapshot(job_id)
            if generation is not None and generation != run:
                await websocket.close(code=1000, reason="Задача перезапущена")
                return
            if value.status != "uploaded":
                generation = run
            if revision != latest:
                await websocket.send_json(value.model_dump(mode="json"))
                revision = latest
            if value.status in {"completed", "stopped", "error"}:
                await websocket.close(code=1000)
                return
            await asyncio.sleep(0.05)

    tasks = [asyncio.create_task(disconnected()), asyncio.create_task(updates())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            with suppress(WebSocketDisconnect, OSError):
                task.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
