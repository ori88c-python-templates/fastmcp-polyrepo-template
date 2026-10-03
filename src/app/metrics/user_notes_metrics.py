"""Prometheus collectors for user-note operations."""

from typing import Final

from prometheus_client import CollectorRegistry, Counter


class UserNotesMetrics:
    """Counters for user-note reads and writes, bound to one Prometheus registry.

    Constructed by the composition root and injected into ``UserNotesService``.
    The registry must be the same one ``PrometheusManager`` exposes at
    ``/metrics``, or scrapes will not see these series.

    Attributes:
        reads_total: Incremented once per ``get_all_notes`` call, including an
            empty list.
        writes_total: Incremented once per ``add_note`` that pushed a note.
    """

    def __init__(self, registry: CollectorRegistry) -> None:
        """Register the read and write counters.

        Args:
            registry: Collector to register with. Must be the same registry
                ``PrometheusManager`` scrapes in production. Tests pass a
                private registry so they do not collide with one another.
        """
        self.reads_total: Final = Counter(
            "user_notes_reads_total",
            "Times UserNotesService.get_all_notes was called.",
            registry=registry,
        )
        self.writes_total: Final = Counter(
            "user_notes_writes_total",
            "Times UserNotesService.add_note pushed a note.",
            registry=registry,
        )
