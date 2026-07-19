"""Adapter protocol: the only layer allowed to know DB specifics."""

from typing import Protocol

from app.core.models import Edge, Entity


class Introspector(Protocol):
    def introspect(self) -> tuple[list[Entity], list[Edge]]:
        """Return all entities and dependency edges for one cluster."""
        ...
