from portfolio.portfolio import Portfolio
from ..interfaces.signal_generator_interface import ISignalGenerator
from data_provider.data_provider import DataProvider
from events.events import DataEvent, SignalEvent
from order_executor.order_executor import OrderExecutor
from ..properties.signal_generator_properties import MACrossoverProps


class StrategyMACrossover(ISignalGenerator):

    def __init__(
        self,
        properties: MACrossoverProps,
    ) -> None:
        self.timeframe = properties.timeframe
        self.fast_ma_period = properties.fast_period if properties.fast_period > 1 else 2
        self.slow_ma_period = properties.slow_period if properties. slow_period > 2 else 3

        if self.fast_ma_period >= self.slow_ma_period:
            raise ValueError(
                f"Fast MA period ({self.fast_ma_period}) must be less than "
                f"Slow MA period ({self.slow_ma_period})."
            )

    def generate_signal(
        self,
        data_event: DataEvent,
        data_provider: DataProvider,
        portfolio: Portfolio,
        order_executor: OrderExecutor
    ) -> SignalEvent:
        symbol = data_event.symbol

        bars = data_provider.get_latest_closed_bars(symbol, self.timeframe, self.slow_ma_period)

        open_positions = portfolio.get_number_of_strategy_open_positions_by_symbol(symbol)

        fast_ma = bars['close'][-self.fast_ma_period:].mean()
        slow_ma = bars['close'].mean()

        if open_positions['LONG'] == 0 and fast_ma > slow_ma:
            if open_positions['SHORT'] > 0:
                order_executor.close_strategy_short_positions_by_symbol(symbol)
            signal = 'BUY'

        elif open_positions['SHORT'] == 0 and fast_ma < slow_ma:
            if open_positions['LONG'] > 0:
                order_executor.close_strategy_long_positions_by_symbol(symbol)
            signal = 'SELL'

        else:
            signal = ''

        if signal != '':
            signal_event = SignalEvent(
                symbol=symbol,
                signal=signal,
                target_order='MARKET',
                target_price=0.0,
                magic_number=portfolio.magic,
                stop_loss=0.0,
                take_profit=0.0
            )
            return signal_event
