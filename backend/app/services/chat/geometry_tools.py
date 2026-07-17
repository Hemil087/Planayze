"""
Geometry Tools — Phase 10

Deterministic tools the chat agent can call against extracted
floor plan data. The LLM never reasons about geometry directly —
it calls these tools, and the tools return factual answers.

Each tool takes a FloorPlanExtraction and room/parameter arguments,
returning a structured result the agent can narrate to the user.

Defensive design:
- All numeric args are explicitly cast to float (LLM may pass them as strings)
- All string args are stripped and lowercased for matching
- external_walls are coerced to Wall enum regardless of whether they
  arrive as enum instances or raw strings
- Every tool returns a structured dict — never raises
"""

from collections import deque
from typing import Any

from app.schemas.extraction import FloorPlanExtraction, Room, Wall


# ── Type coercion helpers ────────────────────────────────────────

def _coerce_float(value: Any, default: float = 0.0) -> float:
    """Cast value to float safely. LLM tool args often arrive as strings."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_wall(value: Any) -> Wall | None:
    """
    Coerce a value to a Wall enum instance.
    Handles Wall enum objects, strings ("N", "S", "E", "W"),
    and lowercased variants.
    """
    if isinstance(value, Wall):
        return value
    if isinstance(value, str):
        try:
            return Wall(value.strip().upper())
        except ValueError:
            return None
    return None


# ── Lookup helpers ───────────────────────────────────────────────

def _find_room(extraction: FloorPlanExtraction, room_name: str) -> Room | None:
    """Find a room by name (case-insensitive, whitespace-tolerant)."""
    normalized = room_name.strip().lower()
    for room in extraction.rooms:
        if room.name.strip().lower() == normalized:
            return room
    return None


def _all_room_names(extraction: FloorPlanExtraction) -> list[str]:
    return [r.name for r in extraction.rooms]


def _build_adjacency(extraction: FloorPlanExtraction) -> dict[str, set[str]]:
    """Build undirected adjacency graph from door connections."""
    graph: dict[str, set[str]] = {}
    for room in extraction.rooms:
        if room.name not in graph:
            graph[room.name] = set()
        for door in room.doors:
            neighbour = door.connects_to
            graph[room.name].add(neighbour)
            if neighbour not in graph:
                graph[neighbour] = set()
            graph[neighbour].add(room.name)
    return graph


# ── Cardinal direction → sun mapping ────────────────────────────

_SUN_DIRECTION: dict[Wall, str] = {
    Wall.E: "morning sun (east-facing)",
    Wall.W: "evening sun (west-facing)",
    Wall.N: "north-facing (indirect light, stays cooler)",
    Wall.S: "south-facing (strong daylight most of the day)",
}


# ── Tool functions ──────────────────────────────────────────────

def room_area(extraction: FloorPlanExtraction, room_name: str) -> dict:
    """
    Return the area and dimensions of a room.

    Returns:
        { "found": bool, "room": str, "area_sqm": float,
          "length_m": float, "width_m": float }
    """
    if not isinstance(room_name, str) or not room_name.strip():
        return {
            "found": False,
            "room": str(room_name),
            "error": "room_name must be a non-empty string.",
        }

    room = _find_room(extraction, room_name)
    if room is None:
        return {
            "found": False,
            "room": room_name,
            "error": (
                f"Room '{room_name}' not found. "
                f"Available rooms: {_all_room_names(extraction)}"
            ),
        }
    return {
        "found": True,
        "room": room.name,
        "area_sqm": room.area_sqm,
        "length_m": room.length_m,
        "width_m": room.width_m,
    }


def fits_furniture(
    extraction: FloorPlanExtraction,
    room_name: str,
    furniture_width_m: Any,
    furniture_depth_m: Any,
    clearance_m: Any = 0.9,
) -> dict:
    """
    Check if furniture of given dimensions fits in a room with clearance.

    The furniture can be placed in either orientation.
    Clearance is added on three sides (not the wall side).

    Returns:
        { "found": bool, "room": str, "fits": bool, ... }
    """
    # Coerce all numeric args — LLM frequently passes these as strings
    furniture_width_m = _coerce_float(furniture_width_m)
    furniture_depth_m = _coerce_float(furniture_depth_m)
    clearance_m = _coerce_float(clearance_m, default=0.9)

    if furniture_width_m <= 0 or furniture_depth_m <= 0:
        return {
            "found": False,
            "room": str(room_name),
            "fits": False,
            "error": "furniture_width_m and furniture_depth_m must be positive numbers.",
        }

    room = _find_room(extraction, room_name)
    if room is None:
        return {
            "found": False,
            "room": room_name,
            "fits": False,
            "error": (
                f"Room '{room_name}' not found. "
                f"Available rooms: {_all_room_names(extraction)}"
            ),
        }

    # Required space = furniture dimension + clearance on 3 sides
    # (assume long side goes against the wall — clearance on remaining sides)
    req_long = max(furniture_width_m, furniture_depth_m) + clearance_m
    req_short = min(furniture_width_m, furniture_depth_m) + clearance_m

    # Try both orientations
    fits_orient_1 = room.length_m >= req_long and room.width_m >= req_short
    fits_orient_2 = room.length_m >= req_short and room.width_m >= req_long

    return {
        "found": True,
        "room": room.name,
        "fits": fits_orient_1 or fits_orient_2,
        "furniture_dims": f"{furniture_width_m}m × {furniture_depth_m}m",
        "clearance_m": clearance_m,
        "required_min": f"{req_short:.2f}m × {req_long:.2f}m",
        "room_dims": f"{room.length_m}m × {room.width_m}m",
    }


def path_between(
    extraction: FloorPlanExtraction,
    room_a: str,
    room_b: str,
) -> dict:
    """
    Find the shortest path between two rooms using BFS on door connections.

    Returns:
        { "found": bool, "path": list[str], "steps": int }
    """
    if not isinstance(room_a, str) or not isinstance(room_b, str):
        return {
            "found": False,
            "path": [],
            "error": "room_a and room_b must be strings.",
        }

    graph = _build_adjacency(extraction)

    # Normalize names against the graph
    norm_a = room_a.strip().lower()
    norm_b = room_b.strip().lower()

    name_a = next((n for n in graph if n.strip().lower() == norm_a), None)
    name_b = next((n for n in graph if n.strip().lower() == norm_b), None)

    if name_a is None:
        return {
            "found": False,
            "path": [],
            "error": (
                f"Room '{room_a}' not found. "
                f"Available rooms: {_all_room_names(extraction)}"
            ),
        }
    if name_b is None:
        return {
            "found": False,
            "path": [],
            "error": (
                f"Room '{room_b}' not found. "
                f"Available rooms: {_all_room_names(extraction)}"
            ),
        }
    if name_a == name_b:
        return {"found": True, "path": [name_a], "steps": 0}

    # BFS
    queue = deque([[name_a]])
    visited = {name_a}

    while queue:
        path = queue.popleft()
        current = path[-1]

        if current == name_b:
            return {"found": True, "path": path, "steps": len(path) - 1}

        for neighbour in graph.get(current, set()):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(path + [neighbour])

    return {
        "found": False,
        "path": [],
        "error": f"No path found between '{room_a}' and '{room_b}'.",
    }


def sun_exposure(extraction: FloorPlanExtraction, room_name: str) -> dict:
    """
    Determine sun exposure based on external wall / window orientations.

    external_walls may contain Wall enum instances or raw strings ("N", "S",
    "E", "W") depending on how Pydantic deserialised the DB JSON — both
    are handled via _coerce_wall.

    Returns:
        { "found": bool, "room": str, "exposures": list[str],
          "has_windows": bool, "external_walls": list[str] }
    """
    if not isinstance(room_name, str) or not room_name.strip():
        return {
            "found": False,
            "room": str(room_name),
            "error": "room_name must be a non-empty string.",
        }

    room = _find_room(extraction, room_name)
    if room is None:
        return {
            "found": False,
            "room": room_name,
            "error": (
                f"Room '{room_name}' not found. "
                f"Available rooms: {_all_room_names(extraction)}"
            ),
        }

    # Collect unique Wall enum instances from both windows and external_walls.
    # Coerce everything — external_walls may be strings or enums.
    orientations: set[Wall] = set()

    for window in room.windows:
        wall = _coerce_wall(window.wall)
        if wall is not None:
            orientations.add(wall)

    for raw_wall in room.external_walls:
        wall = _coerce_wall(raw_wall)
        if wall is not None:
            orientations.add(wall)

    if not orientations:
        return {
            "found": True,
            "room": room.name,
            "exposures": [],
            "has_windows": len(room.windows) > 0,
            "external_walls": [],
            "summary": (
                f"{room.name} is an internal room with no external walls "
                f"or windows — no direct sunlight."
            ),
        }

    # Sort by enum value string for deterministic ordering (E, N, S, W)
    sorted_walls = sorted(orientations, key=lambda w: w.value)
    exposures = [_SUN_DIRECTION[w] for w in sorted_walls]

    return {
        "found": True,
        "room": room.name,
        "exposures": exposures,
        "has_windows": len(room.windows) > 0,
        "external_walls": [w.value for w in sorted_walls],
        "summary": f"{room.name} gets: {', '.join(exposures)}.",
    }


def list_rooms(extraction: FloorPlanExtraction) -> dict:
    """
    List all rooms with their type, area, and dimensions.
    Useful as a first tool call to orient the agent.

    Returns:
        { "rooms": list[{ "name", "type", "area_sqm", "length_m", "width_m" }] }
    """
    return {
        "rooms": [
            {
                "name": r.name,
                "type": r.type.value,
                "area_sqm": r.area_sqm,
                "length_m": r.length_m,
                "width_m": r.width_m,
            }
            for r in extraction.rooms
        ]
    }


# ── Tool registry ───────────────────────────────────────────────

TOOL_REGISTRY = {
    "room_area": room_area,
    "fits_furniture": fits_furniture,
    "path_between": path_between,
    "sun_exposure": sun_exposure,
    "list_rooms": list_rooms,
}

# Tool declarations in OpenAI function-calling JSON Schema format.
# chat_agent.py wraps these in {"type": "function", "function": decl}.
TOOL_DECLARATIONS = [
    {
        "name": "room_area",
        "description": "Get the area and dimensions of a specific room.",
        "parameters": {
            "type": "object",
            "properties": {
                "room_name": {
                    "type": "string",
                    "description": "Name of the room, e.g. 'Bedroom 2', 'Kitchen'",
                },
            },
            "required": ["room_name"],
        },
    },
    {
        "name": "fits_furniture",
        "description": (
            "Check if a piece of furniture fits in a room with walking clearance. "
            "Default clearance is 0.9m on three sides."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "room_name": {
                    "type": "string",
                    "description": "Name of the room to check",
                },
                "furniture_width_m": {
                    "type": "number",
                    "description": "Width of the furniture in metres",
                },
                "furniture_depth_m": {
                    "type": "number",
                    "description": "Depth of the furniture in metres",
                },
                "clearance_m": {
                    "type": "number",
                    "description": "Required clearance in metres (default 0.9)",
                },
            },
            "required": ["room_name", "furniture_width_m", "furniture_depth_m"],
        },
    },
    {
        "name": "path_between",
        "description": "Find the shortest path between two rooms through door connections.",
        "parameters": {
            "type": "object",
            "properties": {
                "room_a": {
                    "type": "string",
                    "description": "Starting room name",
                },
                "room_b": {
                    "type": "string",
                    "description": "Destination room name",
                },
            },
            "required": ["room_a", "room_b"],
        },
    },
    {
        "name": "sun_exposure",
        "description": (
            "Determine which direction a room faces and what sunlight it gets "
            "(morning, evening, etc.)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "room_name": {
                    "type": "string",
                    "description": "Name of the room to check",
                },
            },
            "required": ["room_name"],
        },
    },
    {
        "name": "list_rooms",
        "description": (
            "List all rooms in the floor plan with their type, area, and dimensions. "
            "Call this first if you need to know what rooms exist."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]