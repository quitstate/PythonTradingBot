import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime


class MT5BacktestDataSource:
    def __init__(self, symbol: str, timeframe: str, start_date: str, end_date: str):
        self.symbol = symbol
        self.timeframe = self._map_timeframe(timeframe)
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")

        if not mt5.initialize():
            raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")

        self.data = self._load_historical_data()
        self.index = 0

    def _map_timeframe(self, tf_str: str):
        mapping = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }
        return mapping.get(tf_str.upper(), mt5.TIMEFRAME_M15)

    def _load_historical_data(self) -> pd.DataFrame:
        rates = mt5.copy_rates_range(
            self.symbol,
            self.timeframe,
            self.start_date,
            self.end_date
        )
        if rates is None:
            raise RuntimeError(f"No historical data returned for {self.symbol}")
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_next_bar(self):
        """Devuelve la siguiente barra simulando un nuevo tick"""
        if self.index < len(self.data):
            bar = self.data.iloc[self.index]
            self.index += 1
            return bar
        else:
            return None

    def get_all_data(self) -> pd.DataFrame:
        """Devuelve todos los datos como DataFrame"""
        return self.data

    def reset(self):
        """Reinicia el índice para repetir el backtest"""
        self.index = 0

    def shutdown(self):
        mt5.shutdown()
