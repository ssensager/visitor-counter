"""Real HTTP/WebSocket transport and MJPEG disconnect smoke test."""

import json
import socket
import threading
import time

import httpx
import uvicorn
from websockets.sync.client import connect

from backend.main import create_app
from backend.test_backend import make_video


def test_live_uvicorn_transports(tmp_path, monkeypatch):
    monkeypatch.setenv("VISITOR_USE_MOCK", "1")
    app = create_app(tmp_path / "uploads", tmp_path / "frontend")
    # Reserve the port for this server, rather than racing a free-port lookup.
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5, trust_env=False) as client:
            assert client.get("/api/health").json() == {"status": "ok"}
            data = make_video(tmp_path, frames=100)
            response = client.post("/api/video/upload", files={"file": ("live.mp4", data)})
            assert response.status_code == 200
            job_id = response.json()["job_id"]
            assert client.post(f"/api/video/start/{job_id}").status_code == 200
            with connect(f"ws://127.0.0.1:{port}/ws/stats/{job_id}", open_timeout=5) as ws:
                assert json.loads(ws.recv(timeout=5))["status"] == "processing"
            with client.stream("GET", f"/api/video/stream/{job_id}") as response:
                assert response.status_code == 200
                assert b"Content-Type: image/jpeg" in next(response.iter_bytes())
            # Both viewers disconnected; processing and API must remain usable.
            assert client.get(f"/api/stats/{job_id}").json()["status"] == "processing"
            assert client.post(f"/api/video/stop/{job_id}").json()["status"] == "stopped"
            assert client.post(f"/api/video/start/{job_id}").status_code == 200
            assert client.post(f"/api/video/stop/{job_id}").status_code == 200
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
    assert not thread.is_alive(), "Uvicorn did not shut down after streaming clients disconnected"
