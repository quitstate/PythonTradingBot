import MetaTrader5 as mt5
from types import SimpleNamespace


class Portfolio():

    def __init__(self, magic_number: int, platform_connector=None):  # platform_connector is new
        self.magic = magic_number
        self.platform_connector = platform_connector  # Store it

    def _get_raw_positions(self) -> list:  # Helper
        if self.platform_connector:  # If backtesting connector is provided
            raw_pos_list = []
            for p_dict in self.platform_connector.get_open_positions():
                # Create a mock object that mimics mt5.PositionInfo
                pos_info = SimpleNamespace(
                    ticket=p_dict['ticket'],  # ticket is str (uuid) in backtest
                    symbol=p_dict['symbol'],
                    magic=p_dict.get('magic', self.magic),  # Ensure magic is there
                    volume=p_dict['volume'],
                    price_open=p_dict['entry_price'],
                    type=(mt5.ORDER_TYPE_BUY if p_dict['side'] == 'buy' else mt5.ORDER_TYPE_SELL),
                    sl=p_dict.get('sl', 0.0),
                    tp=p_dict.get('tp', 0.0)
                    # Add other fields like profit, swap, etc., if needed, defaulting to 0
                )
                raw_pos_list.append(pos_info)
            return raw_pos_list
        else:
            positions = mt5.positions_get()
            return list(positions) if positions is not None else []

    def get_open_positions(self) -> tuple:
        """
        Get all open positions for the account.
        """
        return tuple(self._get_raw_positions())

    def get_strategy_open_positions(self) -> tuple:
        """
        Get all open positions for the account with the magic number.
        """
        positions = []
        for position in self._get_raw_positions():
            if position.magic == self.magic:
                positions.append(position)

        return tuple(positions)

    def get_number_of_open_positions_by_symbol(self, symbol: str) -> dict[str, int]:
        """
        Get the number of open positions for a given symbol.
        """
        longs = 0
        shorts = 0
        for position in self._get_raw_positions():
            if position.symbol != symbol:
                continue
            if position.type == mt5.ORDER_TYPE_BUY:
                longs += 1
            elif position.type == mt5.ORDER_TYPE_SELL:
                shorts += 1

        return {'LONG': longs, 'SHORT': shorts, "TOTAL": longs + shorts}

    def get_number_of_strategy_open_positions_by_symbol(self, symbol: str) -> dict[str, int]:
        """
        Get the number of open positions for a given symbol with the magic number.
        """
        longs = 0
        shorts = 0
        for position in self._get_raw_positions():
            if position.symbol != symbol:
                continue
            if position.magic == self.magic:
                if position.type == mt5.ORDER_TYPE_BUY:
                    longs += 1
                elif position.type == mt5.ORDER_TYPE_SELL:
                    shorts += 1

        return {'LONG': longs, 'SHORT': shorts, "TOTAL": longs + shorts}
