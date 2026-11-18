import pytest

from smartcross.config import ROI, Settings
from smartcross.database import Events
from smartcross.lighting import Lighting, Phase


@pytest.mark.parametrize(("box", "expected"), [
    ((20, 0, 80, 70), True), ((18, 0, 18, 58), True),
    ((0, 0, 12, 70), False), ((20, 0, 80, 95), False),
    ((20, 0, 80, 55), False),
])
def test_roi_uses_bottom_center(box, expected):
    assert ROI().contains(box, 100, 100) == expected
    assert ROI().contains(tuple(2 * coordinate for coordinate in box), 200, 200) == expected


def test_confirmation_rejects_isolated_detection():
    light = Lighting()
    assert light.update(False, 0, 1, 2) is None
    assert light.phase == Phase.IDLE
    assert light.update(True, 1, 1, 2) is None
    assert light.phase == Phase.CONFIRMING
    assert light.update(False, 1.5, 1, 2) is None
    assert light.phase == Phase.IDLE
    assert light.update(True, 2, 1, 2) is None
    assert light.update(True, 2.9, 1, 2) is None
    assert light.update(True, 3, 1, 2) == "ativacao"
    assert light.phase == Phase.ACTIVE


def test_hold_and_return():
    light = Lighting()
    light.update(True, 0, 1, 2)
    light.update(True, 1, 1, 2)
    assert light.update(False, 2, 1, 2) is None
    assert light.phase == Phase.HOLDING
    assert light.update(True, 3, 1, 2) is None
    assert light.phase == Phase.ACTIVE
    assert light.active_since == 1
    assert light.update(False, 4, 1, 2) is None
    assert light.update(False, 5.9, 1, 2) is None
    assert light.update(False, 6, 1, 2) == "desativacao"
    assert light.phase == Phase.IDLE
    assert light.active_since is None


def test_zero_hold():
    light = Lighting()
    light.update(True, 0, 1, 0)
    light.update(True, 1, 1, 0)
    assert light.update(False, 2, 1, 0) == "desativacao"


@pytest.mark.parametrize("fields", [
    {}, {"path": "video.mp4"}, {"confidence": True}, {"confidence": float("nan")},
    {"confirmation": 0}, {"hold": -1}, {"hold": "2"},
    {"roi": {"x": .8, "y": 0, "width": .5, "height": .5}},
    {"roi": {"x": 0}},
])
def test_invalid_settings(fields):
    with pytest.raises(ValueError):
        Settings().update(fields)


def test_valid_settings():
    settings = Settings()
    updated = settings.update({"confidence": .65, "hold": 0})
    assert updated.confidence == .65
    assert updated.hold == 0
    assert settings.confidence == .45


def test_persistence(tmp_path):
    path = tmp_path / "nested" / "events.sqlite3"
    db = Events(path)
    db.add("ativacao", "simulation", 2)
    db.add("desativacao", "simulation", 0)
    db = Events(path)
    recent = db.recent()
    assert [event["type"] for event in recent] == ["desativacao", "ativacao"]
    assert recent[1]["people_in_roi"] == 2
    assert recent[1]["source"] == "simulation"
    stats = db.stats()
    assert stats["total"] == 1
    assert len(stats["hours"]) == 24
    assert sum(hour["count"] for hour in stats["hours"]) == 1
