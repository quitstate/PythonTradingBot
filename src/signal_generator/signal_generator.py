from .interfaces.signal_generator_interface import ISignalGenerator
from data_provider.data_provider import DataProvider
from portfolio.portfolio import Portfolio
from order_executor.order_executor import OrderExecutor
from .properties.signal_generator_properties import BaseSignalProps, MACrossoverProps
from .strategies.strategy_ma_crossover import StrategyMACrossover
from events.events import DataEvent
from queue import Queue


class SignalGenerator(ISignalGenerator):
    def __init__(
        self,
        events_queue: Queue,
        data_provider: DataProvider,
        portfolio: Portfolio,
        order_executor: OrderExecutor,
        signal_properties: BaseSignalProps,
    ):
        self.events_queue = events_queue
        self.DATA_PROVIDER = data_provider
        self.PORTFOLIO = portfolio
        self.ORDER_EXECUTOR = order_executor
        self.signal_generator_method = self._get_signal_generator_method(signal_properties)

    def _get_signal_generator_method(self, signal_properties: BaseSignalProps) -> ISignalGenerator:
        if isinstance(signal_properties, MACrossoverProps):
            return StrategyMACrossover(properties=signal_properties)
        else:
            raise ValueError(f"Unknown signal generator properties: {signal_properties}")

    def generate_signal(
        self,
        data_event: DataEvent,
    ) -> None:
        signal_event = self.signal_generator_method.generate_signal(
            data_event,
            self.DATA_PROVIDER,
            self.PORTFOLIO,
            self.ORDER_EXECUTOR,
        )

        if signal_event is not None:
            self.events_queue.put(signal_event)
            print(f"Signal generated: {signal_event.signal} for {signal_event.symbol}")
