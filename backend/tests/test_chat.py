"""
Phase 10 Gate Tests — Geometry Tools

Tests the deterministic geometry tools against synthetic
FloorPlanExtraction data. Agent integration (Gemini function
calling) is tested via curl against the live API.
"""

import pytest
from backend.app.schemas.extraction import (
    FloorPlanExtraction, Room, RoomType, Wall, Window, Door,
)
from backend.app.services.chat.geometry_tools import (
    room_area,
    fits_furniture,
    path_between,
    sun_exposure,
    list_rooms,
)


# ── Fixture ──────────────────────────────────────────────────────

@pytest.fixture
def sample_extraction():
    return FloorPlanExtraction(
        rooms=[
            Room(
                name="Bedroom 1",
                type=RoomType.MASTER_BEDROOM,
                area_sqm=14.0,
                length_m=4.0,
                width_m=3.5,
                external_walls=[Wall.W, Wall.S],
                windows=[
                    Window(wall=Wall.W, width_m=1.5),
                    Window(wall=Wall.S, width_m=1.2),
                ],
                doors=[
                    Door(connects_to="Hallway", width_m=0.9),
                ],
            ),
            Room(
                name="Bedroom 2",
                type=RoomType.BEDROOM,
                area_sqm=7.0,
                length_m=3.1,
                width_m=2.3,
                external_walls=[Wall.N],
                windows=[Window(wall=Wall.N, width_m=1.0)],
                doors=[
                    Door(connects_to="Hallway", width_m=0.9),
                ],
            ),
            Room(
                name="Kitchen",
                type=RoomType.KITCHEN,
                area_sqm=8.0,
                length_m=4.0,
                width_m=2.0,
                external_walls=[Wall.E],
                windows=[Window(wall=Wall.E, width_m=1.0)],
                doors=[
                    Door(connects_to="Living Room", width_m=0.9),
                ],
            ),
            Room(
                name="Living Room",
                type=RoomType.LIVING,
                area_sqm=20.0,
                length_m=5.0,
                width_m=4.0,
                external_walls=[Wall.E, Wall.S],
                windows=[
                    Window(wall=Wall.E, width_m=1.5),
                    Window(wall=Wall.S, width_m=2.0),
                ],
                doors=[
                    Door(connects_to="Kitchen", width_m=0.9),
                    Door(connects_to="Hallway", width_m=1.0),
                    Door(connects_to="ENTRANCE", width_m=1.0),
                ],
            ),
            Room(
                name="Hallway",
                type=RoomType.CORRIDOR,
                area_sqm=5.0,
                length_m=4.0,
                width_m=1.2,
                external_walls=[],
                windows=[],
                doors=[
                    Door(connects_to="Bedroom 1", width_m=0.9),
                    Door(connects_to="Bedroom 2", width_m=0.9),
                    Door(connects_to="Living Room", width_m=1.0),
                ],
            ),
        ],
        total_built_up_sqm=65.0,
        total_carpet_sqm=54.0,
        orientation_north=0,
        floor=3,
        confidence_score=0.85,
    )


# ── room_area ────────────────────────────────────────────────────

class TestRoomArea:
    def test_found(self, sample_extraction):
        result = room_area(sample_extraction, "Bedroom 1")
        assert result["found"] is True
        assert result["area_sqm"] == 14.0
        assert result["length_m"] == 4.0
        assert result["width_m"] == 3.5

    def test_case_insensitive(self, sample_extraction):
        result = room_area(sample_extraction, "bedroom 1")
        assert result["found"] is True

    def test_not_found(self, sample_extraction):
        result = room_area(sample_extraction, "Garage")
        assert result["found"] is False
        assert "error" in result


# ── fits_furniture ───────────────────────────────────────────────

class TestFitsFurniture:
    def test_queen_bed_fits_large_room(self, sample_extraction):
        # Queen bed: 1.5 × 2.0m, Bedroom 1: 4.0 × 3.5m
        result = fits_furniture(sample_extraction, "Bedroom 1", 1.5, 2.0)
        assert result["fits"] is True

    def test_queen_bed_doesnt_fit_small_room(self, sample_extraction):
        # Bedroom 2: 3.1 × 2.3m — too tight with 0.9m clearance
        result = fits_furniture(sample_extraction, "Bedroom 2", 1.5, 2.0)
        assert result["fits"] is False

    def test_small_desk_fits(self, sample_extraction):
        # Small desk: 0.6 × 1.2m — should fit anywhere
        result = fits_furniture(sample_extraction, "Bedroom 2", 0.6, 1.2)
        assert result["fits"] is True

    def test_room_not_found(self, sample_extraction):
        result = fits_furniture(sample_extraction, "Garage", 1.5, 2.0)
        assert result["fits"] is False
        assert "error" in result


# ── path_between ─────────────────────────────────────────────────

class TestPathBetween:
    def test_direct_connection(self, sample_extraction):
        result = path_between(sample_extraction, "Bedroom 1", "Hallway")
        assert result["found"] is True
        assert result["steps"] == 1
        assert result["path"] == ["Bedroom 1", "Hallway"]

    def test_multi_hop(self, sample_extraction):
        # Bedroom 1 → Hallway → Living Room → Kitchen
        result = path_between(sample_extraction, "Bedroom 1", "Kitchen")
        assert result["found"] is True
        assert result["steps"] == 3
        assert "Kitchen" in result["path"]
        assert "Bedroom 1" in result["path"]

    def test_same_room(self, sample_extraction):
        result = path_between(sample_extraction, "Kitchen", "Kitchen")
        assert result["found"] is True
        assert result["steps"] == 0

    def test_room_not_found(self, sample_extraction):
        result = path_between(sample_extraction, "Bedroom 1", "Garage")
        assert result["found"] is False


# ── sun_exposure ─────────────────────────────────────────────────

class TestSunExposure:
    def test_west_south_exposure(self, sample_extraction):
        result = sun_exposure(sample_extraction, "Bedroom 1")
        assert result["found"] is True
        assert len(result["exposures"]) == 2
        assert any("evening" in e for e in result["exposures"])  # west
        assert any("south" in e for e in result["exposures"])

    def test_east_exposure(self, sample_extraction):
        result = sun_exposure(sample_extraction, "Kitchen")
        assert result["found"] is True
        assert any("morning" in e for e in result["exposures"])

    def test_internal_room(self, sample_extraction):
        result = sun_exposure(sample_extraction, "Hallway")
        assert result["found"] is True
        assert result["exposures"] == []
        assert "no direct sunlight" in result["summary"]

    def test_not_found(self, sample_extraction):
        result = sun_exposure(sample_extraction, "Garage")
        assert result["found"] is False


# ── list_rooms ───────────────────────────────────────────────────

class TestListRooms:
    def test_lists_all(self, sample_extraction):
        result = list_rooms(sample_extraction)
        assert len(result["rooms"]) == 5
        names = {r["name"] for r in result["rooms"]}
        assert "Bedroom 1" in names
        assert "Kitchen" in names
        assert "Hallway" in names