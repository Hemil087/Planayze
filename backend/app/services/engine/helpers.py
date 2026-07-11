from uuid import uuid4
from app.schemas.extraction import FloorPlanExtraction, Room, RoomType
from app.schemas.report import Finding, Severity, Category


# -------------------------------------------------------------------
# Finding factory helpers
# -------------------------------------------------------------------

def violation(
    rule_id: str,
    category: Category,
    title: str,
    detail: str,
    room_names: list[str],
) -> Finding:
    return Finding(
        id=str(uuid4()),
        severity=Severity.VIOLATION,
        category=category,
        title=title,
        detail=detail,
        room_names=room_names,
        rule_id=rule_id,
        score_impact=-10,
    )


def tradeoff(
    rule_id: str,
    category: Category,
    title: str,
    detail: str,
    room_names: list[str],
) -> Finding:
    return Finding(
        id=str(uuid4()),
        severity=Severity.TRADEOFF,
        category=category,
        title=title,
        detail=detail,
        room_names=room_names,
        rule_id=rule_id,
        score_impact=-4,
    )


def observation(
    rule_id: str,
    category: Category,
    title: str,
    detail: str,
    room_names: list[str],
    positive: bool = False,
) -> Finding:
    return Finding(
        id=str(uuid4()),
        severity=Severity.OBSERVATION,
        category=category,
        title=title,
        detail=detail,
        room_names=room_names,
        rule_id=rule_id,
        score_impact=0 if positive else -1,
    )


# -------------------------------------------------------------------
# Graph helpers — build adjacency from door connections
# -------------------------------------------------------------------

def build_adjacency(extraction: FloorPlanExtraction) -> dict[str, set[str]]:
    """
    Build an undirected adjacency graph from door connections.
    Keys are room names; values are sets of connected room names.
    ENTRANCE and EXTERIOR are included as virtual nodes.
    """
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


def rooms_by_type(extraction: FloorPlanExtraction, *types: RoomType) -> list[Room]:
    """Return all rooms matching any of the given types."""
    return [r for r in extraction.rooms if r.type in types]


def are_connected(graph: dict[str, set[str]], a: str, b: str) -> bool:
    """Return True if rooms a and b are directly connected by a door."""
    return b in graph.get(a, set())


def path_exists_through(
    graph: dict[str, set[str]],
    start: str,
    end: str,
    through: str,
) -> bool:
    """
    Return True if there exists a shortest path from start → end
    that passes through the given intermediate node.
    Uses BFS.
    """
    from collections import deque

    if start not in graph or end not in graph:
        return False

    # BFS from start — track visited and path
    queue = deque([[start]])
    visited = {start}

    while queue:
        path = queue.popleft()
        current = path[-1]

        if current == end:
            return through in path

        for neighbour in graph.get(current, set()):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(path + [neighbour])

    return False