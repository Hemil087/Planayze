from backend.app.schemas.extraction import FloorPlanExtraction, RoomType
from backend.app.schemas.report import Finding, Category
from backend.app.services.engine.helpers import (
    violation, tradeoff, rooms_by_type,
    build_adjacency, are_connected,
)

BEDROOM_TYPES = {RoomType.BEDROOM, RoomType.MASTER_BEDROOM}
NOISY_ADJACENT = {RoomType.LIVING, RoomType.CORRIDOR}


def run(extraction: FloorPlanExtraction) -> list[Finding]:
    findings: list[Finding] = []
    graph = build_adjacency(extraction)

    bedrooms = rooms_by_type(extraction, *BEDROOM_TYPES)

    # ── PRIV_001: Bedroom door visible from entrance ─────────────
    for bedroom in bedrooms:
        for door in bedroom.doors:
            if door.connects_to.upper() in ("ENTRANCE", "EXTERIOR"):
                findings.append(violation(
                    rule_id="PRIV_001",
                    category=Category.PRIVACY,
                    title=f"Bedroom exposed to entrance — {bedroom.name}",
                    detail=(
                        f"{bedroom.name} opens directly to the building entrance. "
                        f"Guests entering the flat will have a direct sightline into "
                        f"the bedroom, which is a significant privacy concern."
                    ),
                    room_names=[bedroom.name],
                ))

    # ── PRIV_002: Master bedroom adjacent to living / corridor ───
    master_bedrooms = rooms_by_type(extraction, RoomType.MASTER_BEDROOM)
    for master in master_bedrooms:
        noisy_neighbours = []
        for other in extraction.rooms:
            if other.type in NOISY_ADJACENT and are_connected(graph, master.name, other.name):
                noisy_neighbours.append(other.name)

        if noisy_neighbours:
            findings.append(tradeoff(
                rule_id="PRIV_002",
                category=Category.PRIVACY,
                title=f"Master bedroom adjacent to noisy space — {master.name}",
                detail=(
                    f"{master.name} shares a wall with: {', '.join(noisy_neighbours)}. "
                    f"Sound transmission from living areas and corridors will "
                    f"disturb sleep. Ideally the master bedroom should be buffered "
                    f"by bathrooms or utility rooms."
                ),
                room_names=[master.name] + noisy_neighbours,
            ))

    # ── PRIV_003: Entrance opens directly into a bedroom ─────────
    entrance_neighbours = graph.get("ENTRANCE", set())
    for bedroom in bedrooms:
        if bedroom.name in entrance_neighbours:
            findings.append(violation(
                rule_id="PRIV_003",
                category=Category.PRIVACY,
                title=f"Entrance opens into bedroom — {bedroom.name}",
                detail=(
                    f"The main entrance connects directly to {bedroom.name}. "
                    f"There is no buffer space (foyer, corridor, or living room) "
                    f"between the entrance and the sleeping area."
                ),
                room_names=[bedroom.name],
            ))

    return findings