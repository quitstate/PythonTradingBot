from typing import Protocol
from events.events import SignalEvent
from data_source.data_source import DataSource


class IPositionSizer(Protocol):

    def size_signal(self, signal_event: SignalEvent, DATA_SOURCE: DataSource) -> float | None:
        ...
