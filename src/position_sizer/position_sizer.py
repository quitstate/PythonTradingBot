
from events.events import SignalEvent, SizingEvent
from data_provider.data_provider import DataProvider
from .properties.position_sizer_properties import (
    BaseSizingProps,
    FixedSizingProps,
    MinSizingProps,
    RiskPctSizingProps,
)
from .interfaces.position_sizer_interface import IPositionSizer
from .position_sizers.min_size_position_sizer import MinSizePositionSizer
from .position_sizers.fixed_size_position_sizer import FixedSizePositionSizer
from .position_sizers.risk_pct_position_size import RiskPctPositionSizer
import MetaTrader5 as mt5

from queue import Queue


class PositionSizer(IPositionSizer):

    def __init__(self, events_queue: Queue, data_provider: DataProvider, sizing_properties: BaseSizingProps):
        self.events_queue = events_queue
        self.DATA_PROVIDER = data_provider
        self.position_sizing_method = self._get_position_sizing_method(sizing_properties)

    def _get_position_sizing_method(self, sizing_properties: BaseSizingProps) -> IPositionSizer:

        if isinstance(sizing_properties, MinSizingProps):
            return MinSizePositionSizer()

        elif isinstance(sizing_properties, FixedSizingProps):
            return FixedSizePositionSizer(properties=sizing_properties)

        elif isinstance(sizing_properties, RiskPctSizingProps):
            return RiskPctPositionSizer(properties=sizing_properties)

        else:
            raise ValueError(f"Unknown sizing properties type: {type(sizing_properties)}")

    def _create_and_put_sizing_event(self, signal_event: SignalEvent, volume: float) -> None:

        sizing_event = SizingEvent(
            symbol=signal_event.symbol,
            signal=signal_event.signal,
            target_order=signal_event.target_order,
            target_price=signal_event.target_price,
            magic_number=signal_event.magic_number,
            stop_loss=signal_event.stop_loss,
            take_profit=signal_event.take_profit,
            volume=volume,
        )
        self.events_queue.put(sizing_event)

    def size_signal(self, signal_event: SignalEvent) -> None:

        volume = self.position_sizing_method.size_signal(signal_event, self.DATA_PROVIDER)

        if volume < mt5.symbol_info(signal_event.symbol).volume_min:
            volume = mt5.symbol_info(signal_event.symbol).volume_min
        elif volume > mt5.symbol_info(signal_event.symbol).volume_max:
            volume = mt5.symbol_info(signal_event.symbol).volume_max

        self._create_and_put_sizing_event(signal_event, volume)
