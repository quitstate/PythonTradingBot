from anomaly_detector.anomaly_detector import IsolationForestAnomalyDetector
from backtesting.anomaly_detector_mt5.anomaly_detector_mt5 import BacktestIsolationForestAnomalyDetector
from backtesting.sentiment_analyzer_mt5.sentiment_analyzer_mt5 import BacktestSentimentAnalyzer
from .interfaces.strategy_manager_interface import IStrategyManager
from data_source.data_source import DataSource
from portfolio.portfolio import Portfolio
from order_executor.order_executor import OrderExecutor
from .properties.strategy_manager_properties import BaseStrategyProps, MACrossoverProps, RSIProps
from .strategies.strategy_rsi_mr import StrategyRSI
from .strategies.strategy_ma_crossover import StrategyMACrossover
from events.events import DataEvent
from sentiment_analyzer.sentiment_analyzer import SentimentAnalyzer
from queue import Queue


class StrategyManager(IStrategyManager):
    def __init__(
        self,
        events_queue: Queue,
        data_source: DataSource,
        portfolio: Portfolio,
        order_executor: OrderExecutor,
        strategy_properties: BaseStrategyProps,
        sentiment_analyzer: SentimentAnalyzer | BacktestSentimentAnalyzer | None = None,
        anomaly_detector: (
            IsolationForestAnomalyDetector
            | BacktestIsolationForestAnomalyDetector
            | None
        ) = None
    ):
        self.events_queue = events_queue
        self.DATA_SOURCE = data_source
        self.PORTFOLIO = portfolio
        self.ORDER_EXECUTOR = order_executor
        self.SENTIMENT_ANALYZER = sentiment_analyzer
        self.ANOMALY_DETECTOR = anomaly_detector
        self.strategy_manager_method = self._get_strategy_manager_method(strategy_properties)

    def _get_strategy_manager_method(self, strategy_properties: BaseStrategyProps) -> IStrategyManager:
        if isinstance(strategy_properties, MACrossoverProps):
            return StrategyMACrossover(properties=strategy_properties)
        elif isinstance(strategy_properties, RSIProps):
            return StrategyRSI(properties=strategy_properties)
        else:
            raise ValueError(f"Unknown strategy generator properties: {strategy_properties}")

    def generate_strategy(
        self,
        data_event: DataEvent,
    ) -> None:
        strategy_event = self.strategy_manager_method.generate_strategy(
            data_event,
            self.DATA_SOURCE,
            self.PORTFOLIO,
            self.ORDER_EXECUTOR,
            self.SENTIMENT_ANALYZER,
            self.ANOMALY_DETECTOR
        )

        if strategy_event is not None:
            self.events_queue.put(strategy_event)
            print(f"Signal generated: {strategy_event.strategy} for {strategy_event.symbol}")
