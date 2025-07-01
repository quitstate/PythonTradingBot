import queue
from backtesting.data_source_mt5.data_source_mt5 import MT5BacktestDataSource
from typing import Dict, Callable
from events.events import (
    DataEvent,
    StrategyEvent,
    SizingEvent,
    OrderEvent,
    ExecutionEvent,
    PlacedPendingOrderEvent,
)
from position_sizer.position_sizer import PositionSizer
from strategy_manager.strategy_manager import StrategyManager
from risk_manager.risk_manager import RiskManager
from order_executor.order_executor import OrderExecutor
from utils.utils import Utils


class BacktestingDirector():

    def __init__(
        self,
        events_queue: queue.Queue,
        data_source: MT5BacktestDataSource,
        strategy_manager: StrategyManager,
        position_sizer: PositionSizer,
        risk_manager: RiskManager,
        order_executor: OrderExecutor,
    ) -> None:
        self.events_queue = events_queue
        self.DATA_SOURCE = data_source
        self.STRATEGY_MANAGER = strategy_manager
        self.POSITION_SIZER = position_sizer
        self.RISK_MANAGER = risk_manager
        self.ORDER_EXECUTOR = order_executor
        self.contrinue_trading: bool = True
        self.event_handler: Dict[str, Callable] = {
            "DATA": self._handle_data_event,
            "STRATEGY": self._handle_strategy_event,
            "SIZING": self._handle_sizing_event,
            "ORDER": self._handle_order_event,
            "EXECUTION": self._handle_execution_event,
            "PENDING": self._handle_pending_order_event,
        }

    def _handle_data_event(self, event: DataEvent) -> None:
        print(
            f"{Utils.dateprint()} - Receiving DATA EVENT from: {event.symbol} "
            f"- last close price: {event.data.close}"
        )
        self.STRATEGY_MANAGER.generate_strategy(event)

    def _handle_strategy_event(self, event: StrategyEvent) -> None:
        print(
            f"{Utils.dateprint()} - Receiving STRATEGY EVENT for: {event.strategy} from: {event.symbol} "
        )
        self.POSITION_SIZER.size_strategy(event)

    def _handle_sizing_event(self, event: SizingEvent) -> None:
        print(
            f"{Utils.dateprint()} - Receiving SIZING EVENT with position size: {event.volume} "
            f"for: {event.strategy} from: {event.symbol} "
        )
        self.RISK_MANAGER.assess_order(event)

    def _handle_order_event(self, event: OrderEvent) -> None:
        print(
            f"{Utils.dateprint()} - Receiving ORDER EVENT with position size: {event.volume} "
            f"for: {event.strategy} from: {event.symbol} "
        )
        self.ORDER_EXECUTOR.execute_order(event)

    def _handle_execution_event(self, event: ExecutionEvent) -> None:
        print(
            f"{Utils.dateprint()} - Receiving EXECUTION EVENT for: {event.strategy} in {event.symbol} "
            f"with volume: {event.volume} at price: {event.fill_price}  "
        )
        self._process_execution_or_pending_events(event)

    def _handle_pending_order_event(self, event: PlacedPendingOrderEvent) -> None:
        print(
            f"{Utils.dateprint()} - Receiving PLACED PENDING ORDER EVENT for: {event.strategy} "
            f"{event.target_order} "
            f"in {event.symbol} with volume: {event.volume} at price: {event.target_price}  "
        )
        self._process_execution_or_pending_events(event)

    def _process_execution_or_pending_events(self, event: ExecutionEvent | PlacedPendingOrderEvent) -> None:
        """
        Process execution or pending order events.
        This method is a placeholder for future implementation.
        """
        if isinstance(event, ExecutionEvent):
            print(
                (
                    f"{event.symbol} - MARKET ORDER Execution event for {event.symbol} "
                    f"with volume {event.volume} at price {event.fill_price}"
                )
            )
        elif isinstance(event, PlacedPendingOrderEvent):
            print(
                f"{event.symbol} - PENDING ORDER event for {event.symbol} "
                f"with volume {event.volume} at price {event.target_price}"
            )
        else:
            print(f"Unknown event type: {type(event)}")

    def _handle_none_event(self, event: None) -> None:
        """
        Handle None events. This method is a placeholder for future implementation.
        """
        print("Received None event")
        self.contrinue_trading = False

    def _handle_unknown_event(self, event) -> None:
        """
        Handle unknown events. This method is a placeholder for future implementation.
        """
        print(f"Unknown event type: {type(event)}")
        self.contrinue_trading = False

    def run(self) -> None:
        """
        Run loop adaptado para backtesting.
        Recorre datos históricos paso a paso hasta agotarlos.
        """
        while self.DATA_SOURCE.has_data():
            self.DATA_SOURCE.check_for_new_data()

            while not self.events_queue.empty():
                event = self.events_queue.get()
                if event is not None:
                    handler = self.event_handler.get(event.event_type, self._handle_unknown_event)
                    handler(event)
                else:
                    self._handle_none_event(event)

        print("Backtesting finalizado.")
