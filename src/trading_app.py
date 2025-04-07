from platform_connector.platform_connector import PlatformConnector
from data_provider.data_provider import DataProvider
from trading_director.trading_director import TradingDirector
from queue import Queue

if __name__ == "__main__":

    symbols = ["EURUSD", "AUDUSD"]
    timeframe = "M1"

    events_queue = Queue()

    CONNECT = PlatformConnector(symbol_list=symbols)
    DATA_PROVIDER = DataProvider(events_queue=events_queue, symbol_list=symbols, timeframe=timeframe)

    TRADING_DIRECTOR = TradingDirector(events_queue=events_queue, data_provider=DATA_PROVIDER)
    TRADING_DIRECTOR.run()
