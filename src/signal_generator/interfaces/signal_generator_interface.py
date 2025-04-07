from typing import Protocol
from events.events import DataEvent


class ISignalGenerator(Protocol):
    """
    Interface for a signal generator.
    """

    def generate_signal(self, data_event: DataEvent) -> None:
        ...
