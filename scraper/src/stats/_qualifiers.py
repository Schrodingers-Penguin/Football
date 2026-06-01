"""Shared qualifier helpers for stat taggers."""


def get_qualifier(event: dict, name: str) -> str | None:
    for q in event.get("qualifiers", []):
        if q["type"]["displayName"] == name:
            return q.get("value")
    return None


def has_qualifier(event: dict, name: str) -> bool:
    for q in event.get("qualifiers", []):
        if q["type"]["displayName"] == name:
            return True
    return False
