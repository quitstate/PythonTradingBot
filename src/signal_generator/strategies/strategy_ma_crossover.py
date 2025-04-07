from ..interfaces.signal_generator_interface import ISignalGenerator
from data_provider.data_provider import DataProvider
from events.events import DataEvent, SignalEvent
from queue import Queue


class StrategyMACrossover(ISignalGenerator):

    def __init__(
        self,
        events_queue: Queue,
        data_provider: DataProvider,
        timeframe: str,
        fast_ma_period: int,
        slow_ma_period: int
    ) -> None:
        self.events_queue = events_queue
        self.DATA_PROVIDER = data_provider
        self.timeframe = timeframe
        self.fast_ma_period = fast_ma_period if fast_ma_period > 1 else 2
        self.slow_ma_period = slow_ma_period if slow_ma_period > 2 else 3

        if self.fast_ma_period >= self.slow_ma_period:
            raise ValueError(
                f"Fast MA period ({self.fast_ma_period}) must be less than "
                f"Slow MA period ({self.slow_ma_period})."
            )

    def _create_and_put_signal_event(
        self,
        symbol: str,
        signal: str,
        target_order: str,
        target_price: float,
        magic_number: int,
        stop_loss: float,
        take_profit: float
    ) -> None:
        signal_event = SignalEvent(
            symbol=symbol,
            signal=signal,
            target_order=target_order,
            target_price=target_price,
            magic_number=magic_number,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        self.events_queue.put(signal_event)
        print(f"Signal generated: {signal_event}")

    def generate_signal(self, data_event: DataEvent) -> None:
        symbol = data_event.symbol

        bars = self.DATA_PROVIDER.get_latest_closed_bars(symbol, self.timeframe, self.slow_ma_period)

        fast_ma = bars['close'][-self.fast_ma_period:].mean()
        slow_ma = bars['close'].mean()

        if fast_ma > slow_ma:
            signal = 'BUY'
        elif fast_ma < slow_ma:
            signal = 'SELL'
        else:
            signal = ''

        if signal != '':
            self._create_and_put_signal_event(
                symbol=symbol,
                signal=signal,
                target_order='MARKET',
                target_price=0.0,
                magic_number=1234,
                stop_loss=0.0,
                take_profit=0.0
            )
