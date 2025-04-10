import queue
import time
from data_provider.data_provider import DataProvider
from typing import Dict, Callable
from events.events import DataEvent, SignalEvent, SizingEvent
from position_sizer.position_sizer import PositionSizer
from signal_generator.interfaces.signal_generator_interface import ISignalGenerator


class TradingDirector():

    def __init__(
        self,
        events_queue: queue.Queue,
        data_provider: DataProvider,
        signal_generator: ISignalGenerator,
        position_sizer: PositionSizer,
    ) -> None:
        self.events_queue = events_queue
        self.DATA_PROVIDER = data_provider
        self.SIGNAL_GENERATOR = signal_generator
        self.POSITION_SIZER = position_sizer
        self.contrinue_trading: bool = True
        self.event_handler: Dict[str, Callable] = {
            "DATA": self._handle_data_event,
            "SIGNAL": self._handle_signal_event,
            "SIZING": self._handle_sizing_event,
        }

    def _handle_data_event(self, event: DataEvent) -> None:
        print(
            f"{event.data.name} - Receiving new data from: {event.symbol} "
            f"- last close price: {event.data.close}"
        )
        self.SIGNAL_GENERATOR.generate_signal(event)

    def _handle_signal_event(self, event: SignalEvent) -> None:
        print(
            f"{event.signal.name} - Generating signal for: {event.symbol} "
            f"- signal type: {event.signal.name}"
        )
        self.POSITION_SIZER.size_signal(event)

    def _handle_sizing_event(self, event: SizingEvent) -> None:
        print(
            f"{event.signal.name} - Sizing for: {event.symbol} "
            f"- position size: {event.volume}"
        )

    def run(self) -> None:
        """
        Main loop for the trading director. It will run until the continue_trading flag is set to False.
        It will get the next event from the queue and process it.
        """
        while self.contrinue_trading:
            try:
                event = self.events_queue.get(block=False)

            except queue.Empty:
                self.DATA_PROVIDER.check_for_new_data()

            else:
                if event is not None:
                    handler = self.event_handler.get(event.event_type)
                    if handler is not None:
                        handler(event)
                    else:
                        print(f"Unhandled event type: {event.event_type}")
                else:
                    print("Received None event")
                    self.contrinue_trading = False

            time.sleep(1)  # Sleep for a short time to avoid busy waiting

        print("Exiting trading director run loop")
