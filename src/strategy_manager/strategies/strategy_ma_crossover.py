from backtesting.sentiment_analyzer_mt5.sentiment_analyzer_mt5 import BacktestSentimentAnalyzer
from portfolio.portfolio import Portfolio
from anomaly_detector.anomaly_detector import IsolationForestAnomalyDetector  # + Añadir import
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
        anomaly_detector: IsolationForestAnomalyDetector | None = None
    ) -> StrategyEvent | None:  # La estrategia puede no devolver nada
        symbol = data_event.symbol

        # Determinar cuántas barras se necesitan: el máximo entre slow_ma_period y
        # anomaly_detector.window_size
        bars_to_fetch = self.slow_ma_period
        if anomaly_detector and anomaly_detector.trained:
            bars_to_fetch = max(self.slow_ma_period, anomaly_detector.window_size)

        bars = data_source.get_latest_closed_bars(symbol, self.timeframe, bars_to_fetch)

        if len(bars) < self.slow_ma_period:  # No hay suficientes barras para el cálculo de MA
            # print(
            #     f"MA Crossover: Not enough bars ({len(bars)}) for MA calculation "
            #     f"(slow_ma_period: {self.slow_ma_period}) for {symbol}."
            # )
            return None

        open_positions = portfolio.get_number_of_strategy_open_positions_by_symbol(symbol)
        ma_bars = bars.iloc[-self.slow_ma_period:]  # Usar solo las barras necesarias para MA
        fast_ma = ma_bars['close'][-self.fast_ma_period:].mean()
        slow_ma = ma_bars['close'].mean()

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
                # La lógica de cierre de posición opuesta ya está en OrderExecutor
                order_executor.close_strategy_short_positions_by_symbol(symbol)
            strategy = 'BUY'

        elif open_positions['SHORT'] == 0 and fast_ma < slow_ma:
            if open_positions['LONG'] > 0:
                # La lógica de cierre de posición opuesta ya está en OrderExecutor
                order_executor.close_strategy_long_positions_by_symbol(symbol)
            strategy = 'SELL'

        else:
            strategy = ''

        # Modificar la estrategia basada en el sentimiento agregado
        # Solo actuar sobre el sentimiento si hay suficientes noticias analizadas
        # --- Lógica de Detección de Anomalías ---
        if strategy != '' and anomaly_detector and anomaly_detector.trained:
            if len(bars) >= anomaly_detector.window_size:
                # Obtener el slice del DataFrame para la ventana de anomalías
                # El detector de anomalías espera un slice del DataFrame, no solo los precios de cierre
                # Seleccionará las características configuradas desde este slice.
                window_df_slice = bars.iloc[-anomaly_detector.window_size:]

                # Verificar si todas las características requeridas están presentes en window_df_slice
                missing_features = [f for f in anomaly_detector.features if f not in window_df_slice.columns]
                if missing_features:
                    print(
                        f"MA Crossover: Detección de anomalías para {symbol} omitida. "
                        f"Características faltantes en los datos: {missing_features}"
                    )
                else:
                    # El umbral está configurado dentro de la instancia anomaly_detector
                    if anomaly_detector.is_window_anomalous(window_df_slice, threshold=None):
                        print(
                            (
                                f"MA Crossover: Condición de mercado anómala detectada para {symbol} "
                                f"en {data_event.data.name}. Suprimiendo señal {strategy}."
                            )
                        )
                        strategy = ''  # Suprimir señal
                    else:
                        print(
                            f"MA Crossover: Condición de mercado para {symbol} en {data_event.data.name} " +
                            "considerada normal por el detector de anomalías."
                        )
            else:
                print(
                    f"MA Crossover: No hay suficientes barras ({len(bars)}) para la detección de anomalías " +
                    f"(window_size: {anomaly_detector.window_size}) para {symbol}. " +
                    "La señal procede sin verificación de anomalías."
                )
        # --- Fin de la Lógica de Detección de Anomalías ---

        # Aplicar lógica de sentimiento solo si la estrategia no fue suprimida por anomalía
        if strategy != '' and sentiment_analysis_attempted_this_tick:
            print(
                f"MA Crossover: Evaluando sentimiento para {symbol} para la señal {strategy}. " +
                f"Noticias suficientes: {sufficient_news_for_decision}, " +
                f"Puntuación media: {avg_sentiment_score:.2f}, " +
                f"Analizadas: {total_analyzed}"
            )
            if sufficient_news_for_decision:
                if (
                    strategy == 'BUY'
                    and avg_sentiment_score < -0.1
                ):  # Sentimiento negativo fuerte, ignorar COMPRA
                    print(
                        f"MA Crossover: Señal de COMPRA para {symbol} ignorada debido a sentimiento general "
                        f"negativo (Puntuación media: {avg_sentiment_score:.2f})"
                    )
                    strategy = ''
                elif (
                    strategy == 'SELL'
                    and avg_sentiment_score > 0.1
                ):  # Sentimiento positivo fuerte, ignorar VENTA
                    print(
                        f"MA Crossover: Señal de VENTA para {symbol} ignorada debido a sentimiento general "
                        f"positivo (Puntuación media: {avg_sentiment_score:.2f})"
                    )
                    strategy = ''
            else:  # sufficient_news_for_decision es False, pero se intentó el análisis
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
