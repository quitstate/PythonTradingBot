from portfolio.portfolio import Portfolio
from ..interfaces.strategy_manager_interface import IStrategyManager
from data_source.data_source import DataSource
from events.events import DataEvent, StrategyEvent
from order_executor.order_executor import OrderExecutor
from ..properties.strategy_manager_properties import MACrossoverProps


class StrategyMACrossover(IStrategyManager):

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

    def generate_strategy(
        self,
        data_event: DataEvent,
        DATA_SOURCE: DataSource,
        portfolio: Portfolio,
        order_executor: OrderExecutor
    ) -> StrategyEvent:
        symbol = data_event.symbol

        bars = DATA_SOURCE.get_latest_closed_bars(symbol, self.timeframe, self.slow_ma_period)

        open_positions = portfolio.get_number_of_strategy_open_positions_by_symbol(symbol)

        fast_ma = bars['close'][-self.fast_ma_period:].mean()
        slow_ma = bars['close'].mean()

        if open_positions['LONG'] == 0 and fast_ma > slow_ma:
            if open_positions['SHORT'] > 0:
                order_executor.close_strategy_short_positions_by_symbol(symbol)
            strategy = 'BUY'

        elif open_positions['SHORT'] == 0 and fast_ma < slow_ma:
            if open_positions['LONG'] > 0:
                order_executor.close_strategy_long_positions_by_symbol(symbol)
            strategy = 'SELL'

        else:
            strategy = ''

        if strategy != '':
            strategy_event = StrategyEvent(
                symbol=symbol,
                strategy=strategy,
                target_order='MARKET',
                target_price=0.0,
                magic_number=portfolio.magic,
                stop_loss=0.0,
                take_profit=0.0
            )
            return strategy_event
