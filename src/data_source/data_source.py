import MetaTrader5 as mt5
import pandas as pd
from typing import Dict
from datetime import datetime
from events.events import DataEvent
from queue import Queue


class DataSource():
    """Data source class to manage data loading and preprocessing."""

    def __init__(self, events_queue: Queue, symbol_list: list, timeframe: str):

        self.events_queue: Queue = events_queue

        self.symbols: list = symbol_list
        self.timeframe: str = timeframe

        self.last_bar_datetime: Dict[str, datetime] = {symbol: datetime.min for symbol in self.symbols}

    def _map_timeframes(self, timeframe: str) -> int:
        """Map the string representation of timeframes to MetaTrader5
        constants."""
        timeframe_mapping = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1,
            'W1': mt5.TIMEFRAME_W1,
            'MN1': mt5.TIMEFRAME_MN1
        }
        try:
            return timeframe_mapping.get(timeframe, None)
        except KeyError:
            raise ValueError(
                f"Invalid timeframe: {timeframe}. "
                f"Valid options are: {list(timeframe_mapping.keys())}"
            )

    def get_latest_closed_bar(self, symbol: str, timeframe: str) -> pd.Series:
        """Get the latest closed bar for a given symbol and timeframe.
        Args:
            symbol (str): The symbol to fetch data for.
            timeframe (str): The timeframe to fetch data for.
        Returns:
            pd.Series: The latest closed bar data.
        Raises:
            ValueError: If the symbol or timeframe is invalid.
            RuntimeError: If there is an error fetching data from MT5.
        """

        tf = self._map_timeframes(timeframe)
        from_position = 1
        num_bars = 1
        try:
            bars_np_array = mt5.copy_rates_from_pos(
                    symbol,
                    tf,
                    from_position,
                    num_bars,
            )
            if bars_np_array is None or len(bars_np_array) == 0:
                raise ValueError(
                    f"No data received for symbol: {symbol}, timeframe: {timeframe}."
                )

            bars_df = pd.DataFrame(bars_np_array)
            bars_df['time'] = pd.to_datetime(bars_df['time'], unit='s')
            bars_df.set_index('time', inplace=True)
            bars_df.rename(columns={'tick_volume': 'tickvol', 'real_volume': 'vol'}, inplace=True)
            bars_df = bars_df[['open', 'high', 'low', 'close', 'tickvol', 'vol', 'spread']]

        except Exception as e:
            raise RuntimeError(
                f"Error fetching data for symbol: {symbol}, timeframe: {timeframe}. "
                f"MT5 Error: {mt5.last_error()} "
                f"Exception: {str(e)}"
            )

        else:
            if bars_df.empty:
                raise ValueError(
                    f"Empty DataFrame received for symbol: {symbol}, timeframe: {timeframe}."
                )
            else:
                return bars_df.iloc[-1]  # Return the last row as a Series

    def get_latest_closed_bars(self, symbol: str, timeframe: str, num_bars: int = 1) -> pd.DataFrame:

        tf = self._map_timeframes(timeframe)
        from_position = 1
        bars_count = num_bars if num_bars > 0 else 1
        try:
            bars_np_array = mt5.copy_rates_from_pos(
                    symbol,
                    tf,
                    from_position,
                    bars_count,
            )
            if bars_np_array is None or len(bars_np_array) == 0:
                raise ValueError(
                    f"No data received for symbol: {symbol}, timeframe: {timeframe}."
                )

            bars_df = pd.DataFrame(bars_np_array)
            bars_df['time'] = pd.to_datetime(bars_df['time'], unit='s')
            bars_df.set_index('time', inplace=True)
            bars_df.rename(columns={'tick_volume': 'tickvol', 'real_volume': 'vol'}, inplace=True)
            bars_df = bars_df[['open', 'high', 'low', 'close', 'tickvol', 'vol', 'spread']]

        except Exception as e:
            raise RuntimeError(
                f"Error fetching data for symbol: {symbol}, timeframe: {timeframe}. "
                f"MT5 Error: {mt5.last_error()} "
                f"Exception: {str(e)}"
            )

        else:
            if bars_df.empty:
                raise ValueError(
                    f"Empty DataFrame received for symbol: {symbol}, timeframe: {timeframe}."
                )
            else:
                return bars_df.iloc[-num_bars:]  # Return the last num_bars rows as a DataFrame

    def get_latest_tick(self, symbol: str) -> dict:
        """Get the latest tick for a given symbol.
        Args:
            symbol (str): The symbol to fetch data for.
        Returns:
            dict: The latest tick data.
        Raises:
            ValueError: If the symbol is invalid.
            RuntimeError: If there is an error fetching data from MT5.
        """
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                raise ValueError(f"No tick data received for symbol: {symbol}.")

        except Exception as e:
            raise RuntimeError(
                f"Error fetching tick data for symbol: {symbol}. "
                f"MT5 Error: {mt5.last_error()} "
                f"Exception: {str(e)}"
            )

        else:
            return tick._asdict()  # Convert the tick object to a dictionary

    def check_for_new_data(self) -> None:

        for symbol in self.symbols:
            try:
                latest_bar = self.get_latest_closed_bar(symbol, self.timeframe)

                if latest_bar is None:
                    print(f"No data received for symbol: {symbol}.")
                    continue

                if not latest_bar.empty and latest_bar.name > self.last_bar_datetime[symbol]:
                    print(f"New data available for symbol: {symbol}.")
                    self.last_bar_datetime[symbol] = latest_bar.name

                    data_event = DataEvent(symbol=symbol, data=latest_bar)

                    self.events_queue.put(data_event)

            except Exception as e:
                print(f"Error checking for new data for symbol: {symbol}. Error: {str(e)}")
