import os
from platform_connector.platform_connector import PlatformConnector
from data_source.data_source import DataSource
from portfolio.portfolio import Portfolio
from trading_director.trading_director import TradingDirector
from strategy_manager.strategy_manager import StrategyManager
from strategy_manager.properties.strategy_manager_properties import MACrossoverProps, RSIProps
from position_sizer.position_sizer import PositionSizer
from position_sizer.properties.position_sizer_properties import FixedSizingProps
from risk_manager.risk_manager import RiskManager
from risk_manager.properties.risk_manager_properties import MaxLeverageFactorRiskProps
from order_executor.order_executor import OrderExecutor
from notifications.notifications import NotificationService, TelegramNotificationProperties
from sentiment_analyzer.sentiment_analyzer import SentimentAnalyzer
from dotenv import load_dotenv, find_dotenv

from queue import Queue

if __name__ == "__main__":
    load_dotenv(find_dotenv())
    symbols = ["EURUSD"]
    timeframe = "M1"
    USE_SENTIMENT_ANALYZER = True
    magic_number = 12345

    mac_props = MACrossoverProps(
        timeframe=timeframe,
        slow_period=10,
        fast_period=5,
    )

    rsi_props = RSIProps(
        timeframe=timeframe,
        rsi_period=14,
        rsi_upper=70.0,
        rsi_lower=30.0,
        sl_points=200,
        tp_points=400,
    )

    events_queue = Queue()

    SENTIMENT_ANALYZER = None
    if USE_SENTIMENT_ANALYZER:
        NEWS_API_KEY = os.getenv("NEWS_API_KEY")
        if NEWS_API_KEY:
            print(
                f"Sentiment Analysis enabled. NEWS_API_KEY: "
                f"{NEWS_API_KEY[:4]}...{NEWS_API_KEY[-4:]}"
            )
            SENTIMENT_ANALYZER = SentimentAnalyzer(api_key=NEWS_API_KEY)
        else:
            print(
                "WARN: Sentiment Analysis is enabled but NEWS_API_KEY not found in .env file. "
                "News fetching will fail."
            )
            SENTIMENT_ANALYZER = SentimentAnalyzer(api_key=None)
    else:
        print("Sentiment Analysis is disabled by configuration.")

    CONNECT = PlatformConnector(symbol_list=symbols)

    DATA_SOURCE = DataSource(events_queue=events_queue, symbol_list=symbols, timeframe=timeframe)

    PORTFOLIO = Portfolio(magic_number=magic_number)

    ORDER_EXECUTOR = OrderExecutor(
        events_queue=events_queue,
        portfolio=PORTFOLIO,
    )

    STRATEGY_MANAGER = StrategyManager(
        events_queue=events_queue,
        data_source=DATA_SOURCE,
        portfolio=PORTFOLIO,
        order_executor=ORDER_EXECUTOR,
        strategy_properties=mac_props,
        sentiment_analyzer=SENTIMENT_ANALYZER
    )

    POSITION_SIZER = PositionSizer(
        events_queue=events_queue,
        data_source=DATA_SOURCE,
        sizing_properties=FixedSizingProps(volume=0.10)
    )

    RISK_MANAGER = RiskManager(
        events_queue=events_queue,
        data_source=DATA_SOURCE,
        portfolio=PORTFOLIO,
        risk_properties=MaxLeverageFactorRiskProps(max_leverage_factor=5)
    )

    NOTIFICATION = NotificationService(properties=TelegramNotificationProperties(
        token=os.getenv("TOKEN_BOT"),
        chat_id=os.getenv("CHAT_ID"),
    ))

    TRADING_DIRECTOR = TradingDirector(
        events_queue=events_queue,
        data_source=DATA_SOURCE,
        strategy_manager=STRATEGY_MANAGER,
        position_sizer=POSITION_SIZER,
        risk_manager=RISK_MANAGER,
        order_executor=ORDER_EXECUTOR,
        notification_service=NOTIFICATION
    )

    TRADING_DIRECTOR.run()
