import os
from platform_connector.platform_connector import PlatformConnector
from data_provider.data_provider import DataProvider
from portfolio.portfolio import Portfolio
from trading_director.trading_director import TradingDirector
from signal_generator.strategies.strategy_ma_crossover import StrategyMACrossover
from position_sizer.position_sizer import PositionSizer
from position_sizer.properties.position_sizer_properties import FixedSizingProps
from risk_manager.risk_manager import RiskManager
from risk_manager.properties.risk_manager_properties import MaxLeverageFactorRiskProps
from order_executor.order_executor import OrderExecutor
from notifications.notifications import NotificationService, TelegramNotificationProperties

from queue import Queue

if __name__ == "__main__":

    symbols = ["EURUSD"]
    timeframe = "M1"
    slow_ma_period = 10
    fast_ma_period = 5
    magic_number = 12345

    events_queue = Queue()

    CONNECT = PlatformConnector(symbol_list=symbols)

    DATA_PROVIDER = DataProvider(events_queue=events_queue, symbol_list=symbols, timeframe=timeframe)

    PORTFOLIO = Portfolio(magic_number=magic_number)

    ORDER_EXECUTOR = OrderExecutor(
        events_queue=events_queue,
        portfolio=PORTFOLIO,
    )

    SIGNAL_GENERATOR = StrategyMACrossover(
        events_queue=events_queue,
        data_provider=DATA_PROVIDER,
        portfolio=PORTFOLIO,
        order_executor=ORDER_EXECUTOR,
        timeframe=timeframe,
        fast_ma_period=fast_ma_period,
        slow_ma_period=slow_ma_period
    )

    POSITION_SIZER = PositionSizer(
        events_queue=events_queue,
        data_provider=DATA_PROVIDER,
        sizing_properties=FixedSizingProps(volume=0.10)
    )

    RISK_MANAGER = RiskManager(
        events_queue=events_queue,
        data_provider=DATA_PROVIDER,
        portfolio=PORTFOLIO,
        risk_properties=MaxLeverageFactorRiskProps(max_leverage_factor=5)
    )

    NOTIFICATION = NotificationService(properties=TelegramNotificationProperties(
        token=os.getenv("TOKEN_BOT"),
        chat_id=os.getenv("CHAT_ID"),
    ))

    TRADING_DIRECTOR = TradingDirector(
        events_queue=events_queue,
        data_provider=DATA_PROVIDER,
        signal_generator=SIGNAL_GENERATOR,
        position_sizer=POSITION_SIZER,
        risk_manager=RISK_MANAGER,
        order_executor=ORDER_EXECUTOR,
        notification_service=NOTIFICATION
    )

    TRADING_DIRECTOR.run()
