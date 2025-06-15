from backtesting.sentiment_analyzer_mt5.sentiment_analyzer_mt5 import BacktestSentimentAnalyzer
from portfolio.portfolio import Portfolio
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
        sentiment_analyzer: SentimentAnalyzer | BacktestSentimentAnalyzer | None = None
    ) -> StrategyEvent:
        symbol = data_event.symbol

        bars = data_source.get_latest_closed_bars(symbol, self.timeframe, self.slow_ma_period)

        open_positions = portfolio.get_number_of_strategy_open_positions_by_symbol(symbol)

        fast_ma = bars['close'][-self.fast_ma_period:].mean()
        slow_ma = bars['close'].mean()

        # Variables para el sentimiento agregado
        avg_sentiment_score = 0.0
        sufficient_news_for_decision = False
        total_analyzed = 0
        # Esta bandera será True si se intenta el análisis de sentimiento en este tick
        sentiment_analysis_attempted_this_tick = False

        # Controlar la frecuencia de llamadas al sentiment analyzer
        if sentiment_analyzer:
            current_time = datetime.now()
            current_bar_timestamp = data_event.data.name
            if isinstance(current_bar_timestamp, pd.Timestamp):
                current_time = current_bar_timestamp.to_pydatetime()
            else:
                current_time = pd.Timestamp(current_bar_timestamp).to_pydatetime()
            last_check_time_for_symbol = self.last_sentiment_check_time.get(symbol)

            # Por defecto, intentar análisis si el sentiment_analyzer está disponible
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
                sentiment_analysis_attempted_this_tick = True  # Marcar que se intentó
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
                order_executor.close_strategy_short_positions_by_symbol(symbol)
            strategy = 'BUY'

        elif open_positions['SHORT'] == 0 and fast_ma < slow_ma:
            if open_positions['LONG'] > 0:
                order_executor.close_strategy_long_positions_by_symbol(symbol)
            strategy = 'SELL'

        else:
            strategy = ''

        # Modificar la estrategia basada en el sentimiento agregado
        # Solo actuar sobre el sentimiento si hay suficientes noticias analizadas
        if sentiment_analysis_attempted_this_tick:
            print(
                f"MA Crossover: Evaluating sentiment for {symbol} for {strategy}. "
                f"Sufficient news: {sufficient_news_for_decision}, Avg Score: {avg_sentiment_score:.2f}, "
                f"Analyzed: {total_analyzed}"
            )
            if sufficient_news_for_decision:
                if (
                    strategy == 'BUY' and avg_sentiment_score > 0.1
                ):  # Umbral de ejemplo para sentimiento negativo
                    print(
                        f"MA Crossover: BUY signal for {symbol} ignored due to overall "
                        f"positive sentiment (Avg Score: {avg_sentiment_score:.2f})"
                    )
                    strategy = ''
                elif (  # Ejemplo: Ignorar SELL si el sentimiento es muy negativo
                    strategy == 'SELL' and avg_sentiment_score < -0.1
                ):  # Umbral de ejemplo para sentimiento negativo
                    print(
                        f"MA Crossover: SELL signal for {symbol} ignored due to overall "
                        f"negative sentiment (Avg Score: {avg_sentiment_score:.2f})"
                    )
                    strategy = ''
                elif strategy != '':  # Si había una señal y no fue alterada por el sentimiento
                    print(
                        f"MA Crossover: Sentiment score {avg_sentiment_score:.2f} for {symbol} "
                        f"is not strong enough to alter the '{strategy}' signal."
                    )
            else:  # sufficient_news_for_decision es False, pero se intentó el análisis
                print(
                    f"MA Crossover: Not enough news analyzed ({total_analyzed}) for {symbol} "
                    f"to modify strategy based on sentiment, or analysis did not yield sufficient data."
                )

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
