from backend.app.schemas.extraction import FloorPlanExtraction, RoomType
from backend.app.schemas.report import Finding, Category
from backend.app.services.engine.helpers import (
    violation, tradeoff, rooms_by_type,
    build_adjacency, path_exists_through,
)

BEDROOM_TYPES = {RoomType.BEDROOM, RoomType.MASTER_BEDROOM}


def run(extraction: FloorPlanExtraction) -> list[Finding]:
    findings: list[Finding] = []
    graph = build_adjacency(extraction)

    bedrooms  = rooms_by_type(extraction, *BEDROOM_TYPES)
    livings   = rooms_by_type(extraction, RoomType.LIVING)
    corridors = rooms_by_type(extraction, RoomType.CORRIDOR)

    # ── CIRC_001: Path to bedroom passes through living room ─────
    if livings:
        living_names = {r.name for r in livings}
        flagged_bedrooms = []

        for bedroom in bedrooms:
            for living_name in living_names:
                if path_exists_through(graph, "ENTRANCE", bedroom.name, living_name):
                    flagged_bedrooms.append(bedroom.name)
                    break

        if flagged_bedrooms:
            findings.append(tradeoff(
                rule_id="CIRC_001",
                category=Category.CIRCULATION,
                title="Bedrooms accessible only through living room",
                detail=(
                    f"To reach {', '.join(flagged_bedrooms)}, occupants must pass "
                    f"through the living room. This forces a social space crossing "
                    f"for private activity — disruptive when guests are present "
                    f"or family members have different sleep schedules."
                ),
                room_names=flagged_bedrooms + [r.name for r in livings],
            ))

    # ── CIRC_002: Dead-end corridor ──────────────────────────────
    for corridor in corridors:
        connections = graph.get(corridor.name, set())
        # Filter out ENTRANCE/EXTERIOR virtual nodes
        real_connections = {
            c for c in connections
            if c.upper() not in ("ENTRANCE", "EXTERIOR")
        }
        if len(real_connections) <= 1:
            findings.append(tradeoff(
                rule_id="CIRC_002",
                category=Category.CIRCULATION,
                title=f"Dead-end corridor — {corridor.name}",
                detail=(
                    f"{corridor.name} connects to only {len(real_connections)} "
                    f"other space(s). A dead-end corridor is wasted area — "
                    f"it adds to built-up cost without improving connectivity."
                ),
                room_names=[corridor.name],
            ))

    return findings