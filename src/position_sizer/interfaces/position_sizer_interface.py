from typing import Protocol
from events.events import StrategyEvent
from data_source.data_source import DataSource


class IPositionSizer(Protocol):

    def size_strategy(self, strategy_event: StrategyEvent, data_source: DataSource) -> float | None:
        ...
