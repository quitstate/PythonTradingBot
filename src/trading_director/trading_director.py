import queue
import time
from data_provider.data_provider import DataProvider
from typing import Dict, Callable
from events.events import DataEvent


class TradingDirector():

    def __init__(self, events_queue: queue.Queue, data_provider: DataProvider):
        self.events_queue = events_queue
        self.DATA_PROVIDER = data_provider
        self.contrinue_trading: bool = True
        self.event_handler: Dict[str, Callable] = {
            "DATA": self._handle_data_event,
        }

    def _handle_data_event(self, event: DataEvent) -> None:
        print(
            f"{event.data.name} - Receiving new data from: {event.symbol} "
            f"- last close price: {event.data.close}"
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
