from portfolio.portfolio import Portfolio
from ..interfaces.strategy_manager_interface import IStrategyManager
from data_source.data_source import DataSource
from events.events import DataEvent, StrategyEvent
from order_executor.order_executor import OrderExecutor
from ..properties.strategy_manager_properties import RSIProps
import pandas as pd
import numpy as np
import MetaTrader5 as mt5


class StrategyRSI(IStrategyManager):

    def __init__(
        self,
        properties: RSIProps,
    ) -> None:
        self.timeframe = properties.timeframe
        self.rsi_period = properties.rsi_period if properties.rsi_period > 2 else 2

        if properties.rsi_upper > 100 or properties.rsi_upper < 0:
            self.rsi_upper = 70
        else:
            self.rsi_upper = properties.rsi_upper

        if properties.rsi_lower > 100 or properties.rsi_lower < 0:
            self.rsi_lower = 30
        else:
            self.rsi_lower = properties.rsi_lower

        if self.rsi_lower >= self.rsi_upper:
            raise ValueError(
                f"RSI Upper ({self.rsi_lower}) must be less than "
                f"RSI Lower ({self.rsi_upper})."
            )

        if properties.sl_points > 0:
            self.sl_points = properties.sl_points
        else:
            self.sl_points = 0.0

        if properties.tp_points > 0:
            self.tp_points = properties.tp_points
        else:
            self.tp_points = 0.0

    def comput_rsi(self, prices: pd.Series) -> float:

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        average_gain = np.mean(gains[-self.rsi_period:])
        average_loss = np.mean(losses[-self.rsi_period:])
        rs = average_gain / average_loss if average_loss > 0 else 0
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def generate_strategy(
        self,
        data_event: DataEvent,
        DATA_SOURCE: DataSource,
        portfolio: Portfolio,
        order_executor: OrderExecutor
    ) -> StrategyEvent:
        symbol = data_event.symbol

        bars = DATA_SOURCE.get_latest_closed_bars(symbol, self.timeframe, self.rsi_period + 1)

        rsi = self.comput_rsi(bars['close'])

        open_positions = portfolio.get_number_of_strategy_open_positions_by_symbol(symbol)

        last_tick = DATA_SOURCE.get_latest_tick(symbol)

        points = mt5.symbol_info(symbol).point

        if open_positions['LONG'] == 0 and rsi < self.rsi_lower:
            if open_positions['SHORT'] > 0:
                order_executor.close_strategy_short_positions_by_symbol(symbol)
            strategy = 'BUY'
            stop_loss = last_tick['ask'] - self.sl_points * points if self.sl_points > 0 else 0
            take_profit = last_tick['ask'] + self.tp_points * points if self.tp_points > 0 else 0

        elif open_positions['SHORT'] == 0 and rsi > self.rsi_upper:
            if open_positions['LONG'] > 0:
                order_executor.close_strategy_long_positions_by_symbol(symbol)
            strategy = 'SELL'
            stop_loss = last_tick['bid'] + self.sl_points * points if self.sl_points > 0 else 0
            take_profit = last_tick['bid'] - self.tp_points * points if self.tp_points > 0 else 0

        else:
            strategy = ''

        if strategy != '':

            strategy_event = StrategyEvent(
                symbol=symbol,
                strategy=strategy,
                target_order='MARKET',
                target_price=0.0,
                magic_number=portfolio.magic,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            return strategy_event
