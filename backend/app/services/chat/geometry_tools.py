"""
Geometry Tools — Phase 10

Deterministic tools the chat agent can call against extracted
floor plan data. The LLM never reasons about geometry directly —
it calls these tools, and the tools return factual answers.

Each tool takes a FloorPlanExtraction and room/parameter arguments,
returning a structured result the agent can narrate to the user.
"""

from collections import deque

from app.schemas.extraction import FloorPlanExtraction, Room, Wall


# ── Lookup helpers ───────────────────────────────────────────────

def _find_room(extraction: FloorPlanExtraction, room_name: str) -> Room | None:
    """Find a room by name (case-insensitive)."""
    normalized = room_name.strip().lower()
    for room in extraction.rooms:
        if room.name.strip().lower() == normalized:
            return room
    return None


def _all_room_names(extraction: FloorPlanExtraction) -> list[str]:
    """Return all room names in the extraction."""
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

_SUN_DIRECTION = {
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
    room = _find_room(extraction, room_name)
    if room is None:
        return {
            "found": False,
            "room": room_name,
            "error": f"Room '{room_name}' not found. Available rooms: {_all_room_names(extraction)}",
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
    furniture_width_m: float,
    furniture_depth_m: float,
    clearance_m: float = 0.9,
) -> dict:
    """
    Check if furniture of given dimensions fits in a room with clearance.

    The furniture can be placed in either orientation.
    Clearance is added on three sides (not the wall side).

    Returns:
        { "found": bool, "room": str, "fits": bool,
          "required_length_m": float, "required_width_m": float,
          "room_length_m": float, "room_width_m": float }
    """
    room = _find_room(extraction, room_name)
    if room is None:
        return {
            "found": False,
            "room": room_name,
            "fits": False,
            "error": f"Room '{room_name}' not found. Available rooms: {_all_room_names(extraction)}",
        }

    # Furniture + clearance on 3 sides (long side against wall)
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
        "required_min": f"{req_short}m × {req_long}m",
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
    graph = _build_adjacency(extraction)

    # Normalize names
    name_a = None
    name_b = None
    for name in graph:
        if name.strip().lower() == room_a.strip().lower():
            name_a = name
        if name.strip().lower() == room_b.strip().lower():
            name_b = name

    if name_a is None:
        return {"found": False, "path": [], "error": f"Room '{room_a}' not found."}
    if name_b is None:
        return {"found": False, "path": [], "error": f"Room '{room_b}' not found."}
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

    Returns:
        { "found": bool, "room": str, "exposures": list[str],
          "has_windows": bool, "external_walls": list[str] }
    """
    room = _find_room(extraction, room_name)
    if room is None:
        return {
            "found": False,
            "room": room_name,
            "error": f"Room '{room_name}' not found. Available rooms: {_all_room_names(extraction)}",
        }

    # Collect unique orientations from windows and external walls
    orientations: set[Wall] = set()
    for window in room.windows:
        orientations.add(window.wall)
    for wall in room.external_walls:
        orientations.add(wall)

    if not orientations:
        return {
            "found": True,
            "room": room.name,
            "exposures": [],
            "has_windows": len(room.windows) > 0,
            "external_walls": [],
            "summary": f"{room.name} is an internal room with no external walls or windows — no direct sunlight.",
        }

    exposures = [_SUN_DIRECTION[o] for o in sorted(orientations, key=lambda w: w.value)]

    return {
        "found": True,
        "room": room.name,
        "exposures": exposures,
        "has_windows": len(room.windows) > 0,
        "external_walls": [w.value for w in room.external_walls],
        "summary": f"{room.name} gets: {', '.join(exposures)}.",
    }


def list_rooms(extraction: FloorPlanExtraction) -> dict:
    """
    List all rooms with their type and area. Useful as a first tool
    call to orient the agent before answering.

    Returns:
        { "rooms": list[{ "name", "type", "area_sqm" }] }
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

# Gemini tool declarations for function calling
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
        "description": "Check if a piece of furniture fits in a room with walking clearance. Default clearance is 0.9m on three sides.",
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
        "description": "Determine which direction a room faces and what sunlight it gets (morning, evening, etc.).",
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
        "description": "List all rooms in the floor plan with their type, area, and dimensions. Call this first if you need to know what rooms exist.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]