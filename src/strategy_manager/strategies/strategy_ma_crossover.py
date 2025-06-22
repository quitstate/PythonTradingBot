from backtesting.anomaly_detector_mt5.anomaly_detector_mt5 import BacktestIsolationForestAnomalyDetector
from backtesting.sentiment_analyzer_mt5.sentiment_analyzer_mt5 import BacktestSentimentAnalyzer
from portfolio.portfolio import Portfolio
from anomaly_detector.anomaly_detector import IsolationForestAnomalyDetector
from ..interfaces.strategy_manager_interface import IStrategyManager
from data_source.data_source import DataSource
from events.events import DataEvent, StrategyEvent
from order_executor.order_executor import OrderExecutor
from sentiment_analyzer.sentiment_analyzer import SentimentAnalyzer
from datetime import datetime, timedelta
from ..properties.strategy_manager_properties import MACrossoverProps
import pandas as pd


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
        self.last_sentiment_check_time: dict[str, datetime] = {}

    def generate_strategy(
        self,
        data_event: DataEvent,
        data_source: DataSource,
        portfolio: Portfolio,
        order_executor: OrderExecutor,
        sentiment_analyzer: SentimentAnalyzer | BacktestSentimentAnalyzer | None = None,
        anomaly_detector: (
            IsolationForestAnomalyDetector
            | BacktestIsolationForestAnomalyDetector
            | None
        ) = None
    ) -> StrategyEvent | None:  # The strategy may not return anything
        symbol = data_event.symbol

        # Determine how many bars are needed: the maximum between slow_ma_period and
        # anomaly_detector.window_size
        bars_to_fetch = self.slow_ma_period
        if anomaly_detector and anomaly_detector.trained:
            bars_to_fetch = max(self.slow_ma_period, anomaly_detector.window_size)

        bars = data_source.get_latest_closed_bars(symbol, self.timeframe, bars_to_fetch)

        if len(bars) < self.slow_ma_period:  # Not enough bars for MA calculation
            # print(
            #     f"MA Crossover: Not enough bars ({len(bars)}) for MA calculation "
            #     f"(slow_ma_period: {self.slow_ma_period}) for {symbol}."
            # )
            return None

        open_positions = portfolio.get_number_of_strategy_open_positions_by_symbol(symbol)
        ma_bars = bars.iloc[-self.slow_ma_period:]  # Use only the necessary bars for MA
        fast_ma = ma_bars['close'][-self.fast_ma_period:].mean()
        slow_ma = ma_bars['close'].mean()

        # Variables for aggregated sentiment
        avg_sentiment_score = 0.0
        sufficient_news_for_decision = False
        total_analyzed = 0
        # This flag will be True if sentiment analysis is attempted on this tick
        sentiment_analysis_attempted_this_tick = False

        # Control the frequency of calls to the sentiment analyzer
        if sentiment_analyzer:
            current_time = datetime.now()
            current_bar_timestamp = data_event.data.name
            if isinstance(current_bar_timestamp, pd.Timestamp):
                current_time = current_bar_timestamp.to_pydatetime()
            else:
                current_time = pd.Timestamp(current_bar_timestamp).to_pydatetime()
            last_check_time_for_symbol = self.last_sentiment_check_time.get(symbol)

            # By default, attempt analysis if sentiment_analyzer is available
            perform_sentiment_analysis_now = True
            if last_check_time_for_symbol and (
                current_time - last_check_time_for_symbol < timedelta(days=14)
            ):
                print(
                    f"MA Crossover: Sentiment analysis for {symbol} skipped, last check was on "
                    f"{last_check_time_for_symbol.strftime('%Y-%m-%d %H:%M:%S')}."
                )
                perform_sentiment_analysis_now = False

            if perform_sentiment_analysis_now:
                sentiment_analysis_attempted_this_tick = True  # Mark that it was attempted
                try:
                    print(f"MA Crossover: Performing sentiment analysis for {symbol}.")
                    if isinstance(sentiment_analyzer, SentimentAnalyzer):
                        sentiment_info = sentiment_analyzer.analyze_sentiment_last_week(
                            query=symbol, page_size=20
                        )
                    elif isinstance(sentiment_analyzer, BacktestSentimentAnalyzer):
                        sentiment_info = sentiment_analyzer.get_sentiment_for_bar_date(
                            query_ticker=symbol,
                            bar_date=bars.index[-1],
                            lookback_days=7,
                            articles_to_analyze=50
                        )
                    else:
                        sentiment_info = None
                    self.last_sentiment_check_time[symbol] = current_time
                    if sentiment_info and "error" not in sentiment_info:
                        avg_sentiment_score = sentiment_info.get("average_sentiment_score", 0.0)
                        total_analyzed = sentiment_info.get("total_analyzed", 0)
                        sufficient_news_for_decision = total_analyzed >= 3
                        print(
                            f"MA Crossover: Aggregated sentiment for {symbol} (last week): "
                            f"Avg Score={avg_sentiment_score:.2f}, Analyzed={total_analyzed}"
                        )
                except Exception as e:
                    print(f"Error getting sentiment for {symbol}: {e}")

        if open_positions['LONG'] == 0 and fast_ma > slow_ma:
            if open_positions['SHORT'] > 0:
                # The logic for closing the opposite position is already in OrderExecutor
                order_executor.close_strategy_short_positions_by_symbol(symbol)
            strategy = 'BUY'

        elif open_positions['SHORT'] == 0 and fast_ma < slow_ma:
            if open_positions['LONG'] > 0:
                # The logic for closing the opposite position is already in OrderExecutor
                order_executor.close_strategy_long_positions_by_symbol(symbol)
            strategy = 'SELL'

        else:
            strategy = ''

        # Modify the strategy based on aggregated sentiment
        # Only act on sentiment if there is enough news analyzed
        # --- Anomaly Detection Logic ---
        if strategy != '' and anomaly_detector and anomaly_detector.trained:
            if len(bars) >= anomaly_detector.window_size:
                # Get the DataFrame slice for the anomaly window
                # The anomaly detector expects a DataFrame slice, not just the closing prices
                # It will select the configured features from this slice.
                window_df_slice = bars.iloc[-anomaly_detector.window_size:]

                # Check if all required features are present in window_df_slice
                missing_features = [f for f in anomaly_detector.features if f not in window_df_slice.columns]
                if missing_features:
                    print(
                        f"MA Crossover: Anomaly detection for {symbol} skipped. "
                        f"Missing features in data: {missing_features}"
                    )
                else:
                    # The threshold is configured within the anomaly_detector instance
                    if anomaly_detector.is_window_anomalous(window_df_slice, threshold=None):
                        print(
                            (
                                f"MA Crossover: Anomalous market condition detected for {symbol} "
                                f"at {data_event.data.name}. Suppressing {strategy} signal."
                            )
                        )
                        strategy = ''  # Suppress signal
                    else:
                        print(
                            f"MA Crossover: Market condition for {symbol} at {data_event.data.name} " +
                            "considered normal by the anomaly detector."
                        )
            else:
                print(
                    f"MA Crossover: Not enough bars ({len(bars)}) for anomaly detection " +
                    f"(window_size: {anomaly_detector.window_size}) para {symbol}. " +
                    "The signal proceeds without anomaly check."
                )
        # --- End of Anomaly Detection Logic ---

        # Apply sentiment logic only if the strategy was not suppressed by anomaly
        if strategy != '' and sentiment_analysis_attempted_this_tick:
            print(
                f"MA Crossover: Evaluating sentiment for {symbol} for {strategy} signal. " +
                f"Sufficient news: {sufficient_news_for_decision}, " +
                f"Average score: {avg_sentiment_score:.2f}, " +
                f"Analyzed: {total_analyzed}"
            )
            if sufficient_news_for_decision:
                if (
                    strategy == 'BUY'
                    and avg_sentiment_score < -0.1
                ):  # Strong negative sentiment, ignore BUY
                    print(
                        f"MA Crossover: BUY signal for {symbol} ignored due to overall "
                        f"negative sentiment (Average Score: {avg_sentiment_score:.2f})"
                    )
                    strategy = ''
                elif (
                    strategy == 'SELL'
                    and avg_sentiment_score > 0.1
                ):  # Strong positive sentiment, ignore SELL
                    print(
                        f"MA Crossover: SELL signal for {symbol} ignored due to overall "
                        f"positive sentiment (Average Score: {avg_sentiment_score:.2f})"
                    )
                    strategy = ''
            else:  # sufficient_news_for_decision is False, but analysis was attempted
                print(
                    f"MA Crossover: Not enough news analyzed ({total_analyzed}) for {symbol} "
                    f"to modify strategy based on sentiment, or analysis did not yield sufficient data."
                )

        if strategy != '':
            print(f"Signal generated: StrategyType.{strategy} for {symbol}")
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
        return None
