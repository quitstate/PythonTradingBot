import queue
import time
from data_source.data_source import DataSource
from typing import Dict, Callable
from events.events import (
    DataEvent,
    SignalEvent,
    SizingEvent,
    OrderEvent,
    ExecutionEvent,
    PlacedPendingOrderEvent,
)
from position_sizer.position_sizer import PositionSizer
from signal_generator.interfaces.signal_generator_interface import ISignalGenerator
from risk_manager.risk_manager import RiskManager
from order_executor.order_executor import OrderExecutor
from notifications.notifications import NotificationService
from utils.utils import Utils


class TradingDirector():

    def __init__(
        self,
        events_queue: queue.Queue,
        DATA_SOURCE: DataSource,
        signal_generator: ISignalGenerator,
        position_sizer: PositionSizer,
        risk_manager: RiskManager,
        order_executor: OrderExecutor,
        notification_service: NotificationService
    ) -> None:
        self.events_queue = events_queue
        self.DATA_SOURCE = DATA_SOURCE
        self.SIGNAL_GENERATOR = signal_generator
        self.POSITION_SIZER = position_sizer
        self.RISK_MANAGER = risk_manager
        self.ORDER_EXECUTOR = order_executor
        self.NOTIFICATION = notification_service
        self.contrinue_trading: bool = True
        self.event_handler: Dict[str, Callable] = {
            "DATA": self._handle_data_event,
            "SIGNAL": self._handle_signal_event,
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
        self.SIGNAL_GENERATOR.generate_signal(event)

    def _handle_signal_event(self, event: SignalEvent) -> None:
        print(
            f"{Utils.dateprint()} - Receiving SIGNAL EVENT for: {event.signal} from: {event.symbol} "
        )
        self.POSITION_SIZER.size_signal(event)

    def _handle_sizing_event(self, event: SizingEvent) -> None:
        print(
            f"{Utils.dateprint()} - Receiving SIZING EVENT with position size: {event.volume} "
            f"for: {event.signal} from: {event.symbol} "
        )
        self.RISK_MANAGER.assess_order(event)

    def _handle_order_event(self, event: OrderEvent) -> None:
        print(
            f"{Utils.dateprint()} - Receiving ORDER EVENT with position size: {event.volume} "
            f"for: {event.signal} from: {event.symbol} "
        )
        self.ORDER_EXECUTOR.execute_order(event)

    def _handle_execution_event(self, event: ExecutionEvent) -> None:
        print(
            f"{Utils.dateprint()} - Receiving EXECUTION EVENT for: {event.signal} in {event.symbol} "
            f"with volume: {event.volume} at price: {event.fill_price}  "
        )
        self._process_execution_or_pending_events(event)

    def _handle_pending_order_event(self, event: PlacedPendingOrderEvent) -> None:
        print(
            f"{Utils.dateprint()} - Receiving PLACED PENDING ORDER EVENT for: {event.signal} "
            f"{event.target_order} "
            f"in {event.symbol} with volume: {event.volume} at price: {event.fill_price}  "
        )
        self._process_execution_or_pending_events(event)

    def _process_execution_or_pending_events(self, event: ExecutionEvent | PlacedPendingOrderEvent) -> None:
        """
        Process execution or pending order events.
        This method is a placeholder for future implementation.
        """
        if isinstance(event, ExecutionEvent):
            self.NOTIFICATION.send_notification(
                title=f"{event.symbol} - MARKET ORDER",
                message=(
                    f"Execution event for {event.symbol} with volume {event.volume} "
                    f"at price {event.fill_price}"
                )
            )
        elif isinstance(event, PlacedPendingOrderEvent):
            self.NOTIFICATION.send_notification(
                title=f"{event.symbol} - PENDING ORDER",
                message=(
                    f"Pending order event for {event.symbol} with volume {event.volume} "
                    f"at price {event.target_price}"
                )
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
        Main loop for the trading director. It will run until the continue_trading flag is set to False.
        It will get the next event from the queue and process it.
        """
        while self.contrinue_trading:
            try:
                event = self.events_queue.get(block=False)

            except queue.Empty:
                self.DATA_SOURCE.check_for_new_data()

            else:
                if event is not None:
                    handler = self.event_handler.get(event.event_type, self._handle_unknown_event)
                    if handler is not None:
                        handler(event)
                    else:
                        print(f"Unhandled event type: {event.event_type}")
                else:
                    self._handle_none_event(event)

            time.sleep(1)  # Sleep for a short time to avoid busy waiting

        print("Exiting trading director run loop")
