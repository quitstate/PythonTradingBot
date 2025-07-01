from typing import Protocol
from backtesting.sentiment_analyzer_mt5.sentiment_analyzer_mt5 import BacktestSentimentAnalyzer
from events.events import DataEvent
from data_source.data_source import DataSource
from portfolio.portfolio import Portfolio
from sentiment_analyzer.sentiment_analyzer import SentimentAnalyzer
from order_executor.order_executor import OrderExecutor
from events.events import StrategyEvent


class IStrategyManager(Protocol):
    """
    Interface for a strategy generator.
    """

    def generate_strategy(
        self,
        data_event: DataEvent,
        data_source: DataSource,
        portfolio: Portfolio,
        order_executor: OrderExecutor,
        sentiment_analyzer: SentimentAnalyzer | BacktestSentimentAnalyzer | None = None
    ) -> StrategyEvent | None:
        ...
