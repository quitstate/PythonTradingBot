from typing import Protocol
from events.events import DataEvent
from data_source.data_source import DataSource
from portfolio.portfolio import Portfolio
from order_executor.order_executor import OrderExecutor
from events.events import SignalEvent


class ISignalGenerator(Protocol):
    """
    Interface for a signal generator.
    """

    def generate_signal(
        self,
        data_event: DataEvent,
        DATA_SOURCE: DataSource,
        portfolio: Portfolio,
        order_executor: OrderExecutor
    ) -> SignalEvent | None:
        ...
