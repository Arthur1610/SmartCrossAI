import io
import sys
from time import monotonic, sleep
from types import SimpleNamespace

import pytest

from smartcross import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
    app.extensions["smartcross"].close()


def wait_for(client, condition):
    deadline = monotonic() + 3
    while monotonic() < deadline:
        value = client.get("/api/state").json
        if condition(value):
            return value
        sleep(.02)
    pytest.fail(f"Estado esperado não alcançado: {value}")


def test_dashboard_renders_without_camera(client):
    assert b"SMARTCROSS" in client.get("/").data
    assert client.get("/static/dashboard.js").status_code == 200
    assert client.get("/api/state").json["phase"] == "INATIVA"
    assert client.get("/api/stream").status_code == 204
    assert client.get("/api/events").json == []


def test_simulation_end_to_end(client):
    assert client.patch("/api/settings", json={"confirmation": .1, "hold": .2}).status_code == 200
    assert client.post("/api/start").status_code == 200
    assert client.post("/api/source", json={"mode": "webcam"}).status_code == 409
    assert client.post("/api/simulation", json={"count": 2}).status_code == 200
    active = wait_for(client, lambda state: state["leds"])
    assert active["inside"] == 2 and active["fps"] is None
    assert client.post("/api/simulation", json={"count": 0}).status_code == 200
    wait_for(client, lambda state: state["phase"] == "AGUARDANDO DESATIVAÇÃO")
    wait_for(client, lambda state: not state["leds"])
    assert client.get("/api/stats").json["total"] == 1
    assert [event["type"] for event in client.get("/api/events").json] == [
        "desativacao", "saida_roi", "ativacao", "entrada_roi",
    ]
    client.post("/api/stop")
    wait_for(client, lambda state: not state["running"])
    assert client.post("/api/start").status_code == 200


def test_no_webcam_recovers(client, monkeypatch):
    capture = SimpleNamespace(read=lambda: (False, None), release=lambda: None)
    monkeypatch.setitem(sys.modules, "cv2", SimpleNamespace(VideoCapture=lambda index: capture))
    assert client.post("/api/source", json={"mode": "webcam", "camera": 2}).status_code == 200
    client.post("/api/start")
    state = wait_for(client, lambda state: not state["running"])
    assert "Webcam indisponível" in state["error"]
    assert client.post("/api/source", json={"mode": "simulation"}).status_code == 200
    assert client.post("/api/start").status_code == 200


def test_invalid_and_cross_origin_requests(client):
    assert client.post("/api/source", json={"mode": "video", "path": "C:/private.mp4"}).status_code == 400
    assert client.post("/api/source", json={"mode": "webcam", "camera": 10}).status_code == 400
    assert client.put("/api/roi", json={"x": .8}).status_code == 400
    assert client.post("/api/start", headers={"Origin": "https://example.org"}).status_code == 403
    assert client.post("/api/simulation", json={"count": 2}).status_code == 409
    assert client.post("/api/source", data={"mode":"video", "video":(io.BytesIO(b"bad"), "bad.mp4")}).status_code == 400


def test_mp4_upload_uses_fixed_temporary_path_and_cleans_up(client):
    video = b"\x00\x00\x00\x18ftypisom" + b"test"
    response = client.post("/api/source", data={
        "mode": "video", "video": (io.BytesIO(video), "../../private-name.mp4"),
    })
    assert response.status_code == 200
    from pathlib import Path

    path = Path(client.application.extensions["smartcross"].sources.path)
    assert path.name == "input.mp4"
    assert path.read_bytes() == video
    assert client.post("/api/source", json={"mode": "simulation"}).status_code == 200
    assert not path.exists()
