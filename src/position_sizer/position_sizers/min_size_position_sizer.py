from events.events import StrategyEvent
from data_source.data_source import DataSource
from ..interfaces.position_sizer_interface import IPositionSizer
import MetaTrader5 as mt5


class MinSizePositionSizer(IPositionSizer):

    def size_strategy(self, strategy_event: StrategyEvent, DATA_SOURCE: DataSource) -> float:
        volume = mt5.symbol_info(strategy_event.symbol).volume_min
        if volume is None:
            raise ValueError(f"Volume for symbol {strategy_event.symbol} is None")
        if volume < 0.0:
            raise ValueError(f"Volume for symbol {strategy_event.symbol} is negative")
        if volume == 0.0:
            raise ValueError(f"Volume for symbol {strategy_event.symbol} is zero")
        return volume
