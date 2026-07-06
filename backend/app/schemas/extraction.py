from enum import Enum
from pydantic import BaseModel, Field, model_validator


# -------------------------------------------------------------------
# Enums
# -------------------------------------------------------------------

class RoomType(str, Enum):
    BEDROOM        = "BEDROOM"
    MASTER_BEDROOM = "MASTER_BEDROOM"
    LIVING         = "LIVING"
    KITCHEN        = "KITCHEN"
    BATHROOM       = "BATHROOM"
    TOILET         = "TOILET"
    BALCONY        = "BALCONY"
    CORRIDOR       = "CORRIDOR"
    UTILITY        = "UTILITY"
    UNKNOWN        = "UNKNOWN"


class Wall(str, Enum):
    """Cardinal directions for external wall / window orientation."""
    N = "N"
    S = "S"
    E = "E"
    W = "W"


# -------------------------------------------------------------------
# Sub-models
# -------------------------------------------------------------------

class Window(BaseModel):
    """A single window opening on a room."""
    wall: Wall = Field(..., description="Which external wall this window faces")
    width_m: float = Field(..., gt=0, description="Opening width in metres")


class Door(BaseModel):
    """A single door opening connecting this room to another space."""
    connects_to: str = Field(
        ...,
        description=(
            "Name of the adjacent room, or one of the special values: "
            "'ENTRANCE' (opens to building entrance) / 'EXTERIOR' (opens outside)"
        ),
    )
    width_m: float = Field(..., gt=0, description="Door width in metres")


# -------------------------------------------------------------------
# Room
# -------------------------------------------------------------------

class Room(BaseModel):
    """
    A single room as extracted from the floor plan image.
    All spatial values are in metres / square metres.
    """
    name: str = Field(..., description="Label as it appears on the floor plan, e.g. 'Bedroom 2'")
    type: RoomType = Field(..., description="Classified room type")

    # Dimensions
    area_sqm: float  = Field(..., gt=0, description="Floor area in square metres")
    length_m: float  = Field(..., gt=0, description="Longer dimension in metres")
    width_m: float   = Field(..., gt=0, description="Shorter dimension in metres")

    # Openings
    external_walls: list[Wall] = Field(
        default_factory=list,
        description="List of walls that face the building exterior (empty = internal room)",
    )
    windows: list[Window] = Field(
        default_factory=list,
        description="All window openings in this room",
    )
    doors: list[Door] = Field(
        default_factory=list,
        description="All door openings in this room (each door appears in both connected rooms)",
    )

    @model_validator(mode="after")
    def length_gte_width(self) -> "Room":
        """Ensure length is always the longer dimension."""
        if self.length_m < self.width_m:
            self.length_m, self.width_m = self.width_m, self.length_m
        return self


# -------------------------------------------------------------------
# Top-level extraction result
# -------------------------------------------------------------------

class FloorPlanExtraction(BaseModel):
    """
    Complete structured representation of a floor plan as extracted by Gemini.
    This is the shared contract consumed by the rule engine, report builder,
    and Phase C chat agent.
    """
    rooms: list[Room] = Field(..., min_length=1, description="All rooms in the floor plan")

    # Areas
    total_built_up_sqm: float = Field(
        ..., gt=0,
        description="Total built-up area (includes walls, corridors) in sqm",
    )
    total_carpet_sqm: float = Field(
        ..., gt=0,
        description="Total usable carpet area (excludes walls) in sqm",
    )

    # Orientation
    orientation_north: float = Field(
        ...,
        ge=0, lt=360,
        description=(
            "Compass bearing (degrees) that corresponds to 'up' on the plan. "
            "0 = up is true North, 90 = up is East, etc."
        ),
    )

    floor: int = Field(
        default=0,
        description="Floor number (0 = ground, -1 = basement)",
    )

    confidence_score: float = Field(
        ...,
        ge=0.0, le=1.0,
        description="Gemini self-reported confidence in the extraction (0–1)",
    )

    @model_validator(mode="after")
    def carpet_lte_built_up(self) -> "FloorPlanExtraction":
        """Carpet area can never exceed built-up area."""
        if self.total_carpet_sqm > self.total_built_up_sqm:
            raise ValueError(
                f"total_carpet_sqm ({self.total_carpet_sqm}) cannot exceed "
                f"total_built_up_sqm ({self.total_built_up_sqm})"
            )
        return self