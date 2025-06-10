import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from events.events import DataEvent
from queue import Queue


class MT5BacktestDataSource:
    def __init__(self, events_queue: Queue, symbols: list, timeframe: str, start_date: str, end_date: str):
        self.events_queue = events_queue
        self.symbols = symbols
        self.timeframe = self._map_timeframe(timeframe)
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        if not mt5.initialize():
            print(
                f"MT5 initialization failed: {mt5.last_error()}, "
                "proceeding without MT5 for backtest data loading if possible."
            )
        self.data = self._load_historical_data()
        self.index = 0
        self.pointer = 0

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
            self.symbols[0],
            self.timeframe,
            self.start_date,
            self.end_date
        )
        if rates is None or len(rates) == 0:
            raise RuntimeError(
                f"No historical data returned for {self.symbols[0]} "
                f"from {self.start_date} to {self.end_date}"
            )
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.rename(columns={'tick_volume': 'tickvol', 'real_volume': 'vol'}, inplace=True)
        if 'spread' not in df.columns:
            df['spread'] = 0

        expected_cols = ['open', 'high', 'low', 'close', 'tickvol', 'vol', 'spread']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = 0.0

        return df

    def has_data(self):
        return self.pointer < len(self.data)

    def check_for_new_data(self):
        if self.has_data():
            bar_series = self.data.iloc[self.pointer].copy()
            bar_series.name = self.data.index[self.pointer]
            event = DataEvent(
                symbol=self.symbols[0],
                data=bar_series,
                event_type="DATA"
            )
            self.events_queue.put(event)
            self.pointer += 1

    def get_next_bar(self):
        if self.index < len(self.data):
            bar = self.data.iloc[self.index]
            self.index += 1
            return bar
        else:
            return None

    def get_all_data(self) -> pd.DataFrame:
        return self.data

    def reset(self):
        self.index = 0

    def get_latest_closed_bars(self, symbol: str, timeframe: str, num_bars: int = 1) -> pd.DataFrame:
        if self.pointer == 0:
            return pd.DataFrame(columns=self.data.columns)
        start_index = max(0, self.pointer - num_bars)
        bars_df = self.data.iloc[start_index:self.pointer]
        return bars_df

    def get_latest_tick(self, symbol: str) -> dict:
        if self.pointer == 0:
            if len(self.data) > 0:
                current_bar_data = self.data.iloc[0]
            else:
                raise RuntimeError("get_latest_tick called before any data was loaded/processed in backtest.")
        else:
            current_bar_data = self.data.iloc[self.pointer - 1]

        return {
            "time": int(current_bar_data.name.timestamp()),
            "bid": float(current_bar_data['close']),
            "ask": float(current_bar_data['close']),
            "last": float(current_bar_data['close']),
            "volume": float(current_bar_data.get('vol', 0)),
            "time_msc": int(current_bar_data.name.timestamp() * 1000),
            "flags": 0,
            "volume_real": float(current_bar_data.get('vol', 0))
        }

    def shutdown(self):
        mt5.shutdown()
