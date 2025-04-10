from events.events import SignalEvent
from data_provider.data_provider import DataProvider
from ..interfaces.position_sizer_interface import IPositionSizer
import MetaTrader5 as mt5


class MinSizePositionSizer(IPositionSizer):

    def size_signal(self, signal_event: SignalEvent, data_provider: DataProvider) -> float:
        volume = mt5.symbol_info(signal_event.symbol).volume_min
        if volume is None:
            raise ValueError(f"Volume for symbol {signal_event.symbol} is None")
        if volume < 0.0:
            raise ValueError(f"Volume for symbol {signal_event.symbol} is negative")
        if volume == 0.0:
            raise ValueError(f"Volume for symbol {signal_event.symbol} is zero")
        return volume
