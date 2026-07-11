from backend.app.schemas.extraction import FloorPlanExtraction, RoomType
from backend.app.schemas.report import Finding, Category
from backend.app.services.engine.helpers import (
    violation, tradeoff, rooms_by_type,
    build_adjacency, are_connected,
)

WET_TYPES      = {RoomType.BATHROOM, RoomType.TOILET}
NOISY_TYPES    = {RoomType.UTILITY}
DINING_TYPES   = {RoomType.LIVING, RoomType.KITCHEN}


def run(extraction: FloorPlanExtraction) -> list[Finding]:
    findings: list[Finding] = []
    graph = build_adjacency(extraction)

    kitchens   = rooms_by_type(extraction, RoomType.KITCHEN)
    wet_rooms  = rooms_by_type(extraction, *WET_TYPES)
    utilities  = rooms_by_type(extraction, RoomType.UTILITY)
    bedrooms   = rooms_by_type(extraction, RoomType.BEDROOM, RoomType.MASTER_BEDROOM)

    # ── ADJ_001: Kitchen adjacent to toilet / bathroom ───────────
    for kitchen in kitchens:
        for wet in wet_rooms:
            if are_connected(graph, kitchen.name, wet.name):
                findings.append(violation(
                    rule_id="ADJ_001",
                    category=Category.ADJACENCY,
                    title=f"Kitchen adjacent to wet room — {kitchen.name} / {wet.name}",
                    detail=(
                        f"{kitchen.name} shares a wall with {wet.name}. "
                        f"NBC Part 9 prohibits direct adjacency between food preparation "
                        f"areas and sanitary spaces due to hygiene and odour concerns. "
                        f"There should be a buffer space between them."
                    ),
                    room_names=[kitchen.name, wet.name],
                ))

    # ── ADJ_002: Toilet door facing kitchen or dining area ────────
    for wet in wet_rooms:
        for door in wet.doors:
            connected_room = next(
                (r for r in extraction.rooms if r.name == door.connects_to),
                None,
            )
            if connected_room and connected_room.type in DINING_TYPES:
                findings.append(violation(
                    rule_id="ADJ_002",
                    category=Category.ADJACENCY,
                    title=f"Toilet door faces {connected_room.name}",
                    detail=(
                        f"The door of {wet.name} opens directly towards "
                        f"{connected_room.name}. NBC prohibits toilet doors "
                        f"facing food preparation or dining areas — "
                        f"this is a hygiene and social comfort concern."
                    ),
                    room_names=[wet.name, connected_room.name],
                ))

    # ── ADJ_003: Bedroom sharing wall with utility / lift shaft ──
    for bedroom in bedrooms:
        for utility in utilities:
            if are_connected(graph, bedroom.name, utility.name):
                findings.append(tradeoff(
                    rule_id="ADJ_003",
                    category=Category.ADJACENCY,
                    title=f"Bedroom adjacent to utility — {bedroom.name}",
                    detail=(
                        f"{bedroom.name} shares a wall with {utility.name}. "
                        f"Utility rooms and lift shafts generate mechanical noise "
                        f"that can disturb sleep. Consider acoustic treatment "
                        f"or verify if adequate sound insulation is provided."
                    ),
                    room_names=[bedroom.name, utility.name],
                ))

    return findings