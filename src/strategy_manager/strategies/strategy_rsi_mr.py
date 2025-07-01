from backtesting.sentiment_analyzer_mt5.sentiment_analyzer_mt5 import BacktestSentimentAnalyzer
from portfolio.portfolio import Portfolio
from ..interfaces.strategy_manager_interface import IStrategyManager
from data_source.data_source import DataSource
from events.events import DataEvent, StrategyEvent
from order_executor.order_executor import OrderExecutor
from sentiment_analyzer.sentiment_analyzer import SentimentAnalyzer
from datetime import datetime, timedelta
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
        self.last_sentiment_check_time: dict[str, datetime] = {}

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
        data_source: DataSource,
        portfolio: Portfolio,
        order_executor: OrderExecutor,
        sentiment_analyzer: SentimentAnalyzer | BacktestSentimentAnalyzer | None = None
    ) -> StrategyEvent:
        symbol = data_event.symbol

        bars = data_source.get_latest_closed_bars(symbol, self.timeframe, self.rsi_period + 1)

        rsi = self.comput_rsi(bars['close'])

        open_positions = portfolio.get_number_of_strategy_open_positions_by_symbol(symbol)

        last_tick = data_source.get_latest_tick(symbol)

        points = mt5.symbol_info(symbol).point

        # Variables for aggregated sentiment
        avg_sentiment_score = 0.0
        sufficient_news_for_decision = False

        # Control the frequency of calls to the sentiment analyzer
        if sentiment_analyzer:
            current_time = datetime.now()
            last_check_time_for_symbol = self.last_sentiment_check_time.get(symbol)

            perform_sentiment_analysis = True
            if last_check_time_for_symbol and (
                current_time - last_check_time_for_symbol < timedelta(days=14)
            ):
                print(
                    f"RSI: Sentiment analysis for {symbol} skipped, last check was on "
                    f"{last_check_time_for_symbol.strftime('%Y-%m-%d %H:%M:%S')}."
                )
                perform_sentiment_analysis = False

            if perform_sentiment_analysis:
                try:
                    print(f"RSI: Performing sentiment analysis for {symbol}.")
                    sentiment_info = sentiment_analyzer.analyze_sentiment_last_week(
                        query=symbol, page_size=10
                    )
                    self.last_sentiment_check_time[symbol] = current_time
                    if sentiment_info and "error" not in sentiment_info:
                        avg_sentiment_score = sentiment_info.get("average_sentiment_score", 0.0)
                        total_analyzed = sentiment_info.get("total_analyzed", 0)
                        sufficient_news_for_decision = total_analyzed >= 3
                        print(
                            f"RSI: Aggregated sentiment for {symbol} (last week): "
                            f"Avg Score={avg_sentiment_score:.2f}, Analyzed={total_analyzed}"
                        )
                except Exception as e:
                    print(f"Error getting sentiment for {symbol}: {e}")

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

        # Modify the strategy based on aggregated sentiment
        if sufficient_news_for_decision:
            # Example: if the average sentiment is markedly negative, do not buy.
            if strategy == 'BUY' and avg_sentiment_score < -0.15:  # Stricter threshold for RSI
                print(
                    f"RSI: BUY signal for {symbol} ignored due to strong overall NEGATIVE "
                    f"sentiment (Avg Score: {avg_sentiment_score:.2f})"
                )
                strategy = ''
            # Example: if the average sentiment is markedly positive, do not short sell.
            elif strategy == 'SELL' and avg_sentiment_score > 0.15:  # Stricter threshold for RSI
                print(
                    f"RSI: SELL signal for {symbol} ignored due to strong overall POSITIVE "
                    f"sentiment (Avg Score: {avg_sentiment_score:.2f})"
                )
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
