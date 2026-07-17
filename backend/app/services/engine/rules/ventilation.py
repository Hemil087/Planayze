from app.schemas.extraction import FloorPlanExtraction, RoomType, Room
from app.schemas.report import Finding, Category
from app.services.engine.helpers import violation, tradeoff, observation

WINDOW_FLOOR_RATIO_MIN = 0.10   # NBC 2016 Cl. 8.1 — window area / floor area
STANDARD_WINDOW_HEIGHT = 1.2    # metres — assumed height for area calc
BALCONY_DOOR_HEIGHT = 2.1       # metres — balcony doors are typically full height

# Rooms that MUST have natural light/ventilation per NBC 2016
HABITABLE_TYPES = {
    RoomType.BEDROOM,
    RoomType.MASTER_BEDROOM,
    RoomType.LIVING,
    RoomType.KITCHEN,
}


# ── Balcony helpers ──────────────────────────────────────────────

def _build_balcony_map(extraction: FloorPlanExtraction) -> dict[str, Room]:
    """Return a name → Room map for all balcony-type rooms."""
    return {
        r.name: r
        for r in extraction.rooms
        if r.type == RoomType.BALCONY
    }


def _get_balcony_benefits(room: Room, balcony_map: dict[str, Room]) -> dict:
    """
    Determine what ventilation and light benefits a room gets from
    an adjacent balcony.

    In Indian apartment design, a balcony is a primary source of
    light and air — a room with a balcony door has full exterior
    exposure through it. The balcony door is treated as:
      - A large opening (door width × full height) for light ratio
      - An additional wall direction for cross-ventilation

    Returns:
        has_balcony      — bool
        balcony_walls    — set of Wall enums from the balcony's external_walls
        balcony_opening_area — float (sqm), door width × door height
        balcony_names    — list[str] for detail messages
    """
    has_balcony = False
    balcony_walls: set = set()
    balcony_opening_area = 0.0
    balcony_names: list[str] = []

    for door in room.doors:
        if door.connects_to in balcony_map:
            balcony = balcony_map[door.connects_to]
            has_balcony = True
            balcony_names.append(balcony.name)
            for wall in balcony.external_walls:
                balcony_walls.add(wall)
            # Balcony door counts as a full-height glazed opening
            balcony_opening_area += door.width_m * BALCONY_DOOR_HEIGHT

    return {
        "has_balcony": has_balcony,
        "balcony_walls": balcony_walls,
        "balcony_opening_area": balcony_opening_area,
        "balcony_names": balcony_names,
    }


# ── Rule runner ──────────────────────────────────────────────────

def run(extraction: FloorPlanExtraction) -> list[Finding]:
    findings: list[Finding] = []
    balcony_map = _build_balcony_map(extraction)

    for room in extraction.rooms:
        if room.type not in HABITABLE_TYPES:
            continue

        balcony = _get_balcony_benefits(room, balcony_map)

        # ── VENT_001: No external walls ──────────────────────────
        # A balcony connection counts as exterior exposure —
        # skip violation if the room has balcony access.
        if not room.external_walls:
            if balcony["has_balcony"]:
                findings.append(observation(
                    rule_id="VENT_001_BAL",
                    category=Category.VENTILATION,
                    title=f"Ventilation via balcony — {room.name}",
                    detail=(
                        f"{room.name} has no direct external walls but connects to "
                        f"{', '.join(balcony['balcony_names'])}, which provides "
                        f"exterior exposure for light and air."
                    ),
                    room_names=[room.name],
                    positive=True,
                ))
            else:
                findings.append(violation(
                    rule_id="VENT_001",
                    category=Category.VENTILATION,
                    title=f"No natural ventilation — {room.name}",
                    detail=(
                        f"{room.name} has no external walls. "
                        f"NBC 2016 requires all habitable rooms to have "
                        f"at least one external wall for natural light and ventilation. "
                        f"This room will rely entirely on mechanical ventilation."
                    ),
                    room_names=[room.name],
                ))

        # ── VENT_002: Window-to-floor-area ratio ─────────────────
        # Balcony doors count as glazed openings for light purposes.
        if room.area_sqm > 0:
            window_area = sum(
                w.width_m * STANDARD_WINDOW_HEIGHT
                for w in room.windows
            )
            effective_area = window_area + balcony["balcony_opening_area"]
            ratio = effective_area / room.area_sqm

            if not room.windows and not balcony["has_balcony"]:
                # No windows, no balcony — clear violation
                findings.append(violation(
                    rule_id="VENT_002",
                    category=Category.VENTILATION,
                    title=f"No windows — {room.name}",
                    detail=(
                        f"{room.name} has no windows. "
                        f"NBC 2016 Cl. 8.1 requires windows in all habitable rooms."
                    ),
                    room_names=[room.name],
                ))

            elif not room.windows and balcony["has_balcony"]:
                # No direct windows but balcony provides light —
                # flag as tradeoff, not violation
                findings.append(tradeoff(
                    rule_id="VENT_002",
                    category=Category.VENTILATION,
                    title=f"Light via balcony only — {room.name}",
                    detail=(
                        f"{room.name} has no direct windows but receives light through "
                        f"{', '.join(balcony['balcony_names'])}. "
                        f"Natural light depends entirely on the balcony door being open."
                    ),
                    room_names=[room.name],
                ))

            elif room.windows and ratio < WINDOW_FLOOR_RATIO_MIN:
                if balcony["has_balcony"]:
                    # Balcony brings effective ratio above threshold — positive observation
                    findings.append(observation(
                        rule_id="VENT_002_POS",
                        category=Category.VENTILATION,
                        title=f"Adequate light with balcony — {room.name}",
                        detail=(
                            f"{room.name} has a direct window ratio of {window_area / room.area_sqm:.1%} "
                            f"(below the 10% NBC minimum), but the balcony door adds "
                            f"{balcony['balcony_opening_area']:.1f} sqm of glazed area, "
                            f"bringing effective ratio to {ratio:.1%}."
                        ),
                        room_names=[room.name],
                        positive=True,
                    ))
                else:
                    findings.append(violation(
                        rule_id="VENT_002",
                        category=Category.VENTILATION,
                        title=f"Insufficient window area — {room.name}",
                        detail=(
                            f"{room.name} has a window-to-floor ratio of {ratio:.1%}. "
                            f"NBC 2016 Cl. 8.1 requires at least {WINDOW_FLOOR_RATIO_MIN:.0%}. "
                            f"Insufficient natural light will make the room feel dark "
                            f"and increase electricity costs."
                        ),
                        room_names=[room.name],
                    ))

        # ── VENT_003: Cross-ventilation check ────────────────────
        # Balcony walls count as additional opening directions.
        window_walls = {w.wall for w in room.windows}
        effective_walls = window_walls | balcony["balcony_walls"]

        has_any_opening = bool(room.windows) or balcony["has_balcony"]

        if has_any_opening and room.external_walls:
            if len(effective_walls) >= 2:
                source = []
                if len(window_walls) >= 2:
                    source.append(f"windows on {len(window_walls)} walls")
                elif window_walls:
                    source.append(f"a window on {list(window_walls)[0]}")
                if balcony["has_balcony"]:
                    source.append(
                        f"balcony access ({', '.join(str(w) for w in balcony['balcony_walls'])})"
                    )
                findings.append(observation(
                    rule_id="VENT_003_POS",
                    category=Category.VENTILATION,
                    title=f"Good cross-ventilation — {room.name}",
                    detail=(
                        f"{room.name} achieves cross-ventilation via "
                        f"{' and '.join(source)}, "
                        f"enabling natural airflow through the room."
                    ),
                    room_names=[room.name],
                    positive=True,
                ))
            else:
                # Single-direction opening
                direction = list(effective_walls)[0] if effective_walls else "unknown"
                findings.append(tradeoff(
                    rule_id="VENT_003",
                    category=Category.VENTILATION,
                    title=f"No cross-ventilation — {room.name}",
                    detail=(
                        f"{room.name} has openings on only one wall ({direction}). "
                        f"Cross-ventilation requires openings on at least two walls — "
                        f"without it, the room will trap heat and have poor air circulation."
                    ),
                    room_names=[room.name],
                ))

    return findings