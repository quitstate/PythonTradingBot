from platform_connector.platform_connector import PlatformConnector
from data_provider.data_provider import DataProvider
from portfolio.portfolio import Portfolio
from trading_director.trading_director import TradingDirector
from signal_generator.strategies.strategy_ma_crossover import StrategyMACrossover
from position_sizer.position_sizer import PositionSizer
from position_sizer.properties.position_sizer_properties import MinSizingProps

from queue import Queue

if __name__ == "__main__":

    symbols = ["EURUSD", "AUDUSD"]
    timeframe = "M1"
    slow_ma_period = 50
    fast_ma_period = 25
    magic_number = 12345

    events_queue = Queue()

    CONNECT = PlatformConnector(symbol_list=symbols)

    DATA_PROVIDER = DataProvider(events_queue=events_queue, symbol_list=symbols, timeframe=timeframe)

    PORTFOLIO = Portfolio(magic_number=magic_number)

    SIGNAL_GENERATOR = StrategyMACrossover(
        events_queue=events_queue,
        data_provider=DATA_PROVIDER,
        portfolio=PORTFOLIO,
        timeframe=timeframe,
        fast_ma_period=fast_ma_period,
        slow_ma_period=slow_ma_period
    )

    POSITION_SIZER = PositionSizer(
        events_queue=events_queue,
        data_provider=DATA_PROVIDER,
        sizing_properties=MinSizingProps()
    )

    TRADING_DIRECTOR = TradingDirector(
        events_queue=events_queue,
        data_provider=DATA_PROVIDER,
        signal_generator=SIGNAL_GENERATOR,
        position_sizer=POSITION_SIZER,
    )
    TRADING_DIRECTOR.run()
