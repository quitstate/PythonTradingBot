
from events.events import StrategyEvent, SizingEvent
from data_source.data_source import DataSource
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

    def __init__(self, events_queue: Queue, data_source: DataSource, sizing_properties: BaseSizingProps):
        self.events_queue = events_queue
        self.DATA_SOURCE = data_source
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

    def _create_and_put_sizing_event(self, strategy_event: StrategyEvent, volume: float) -> None:

        sizing_event = SizingEvent(
            symbol=strategy_event.symbol,
            strategy=strategy_event.strategy,
            target_order=strategy_event.target_order,
            target_price=strategy_event.target_price,
            magic_number=strategy_event.magic_number,
            stop_loss=strategy_event.stop_loss,
            take_profit=strategy_event.take_profit,
            volume=volume,
        )
        self.events_queue.put(sizing_event)

    def size_strategy(self, strategy_event: StrategyEvent) -> None:

        volume = self.position_sizing_method.size_strategy(strategy_event, self.DATA_SOURCE)

        if volume < mt5.symbol_info(strategy_event.symbol).volume_min:
            volume = mt5.symbol_info(strategy_event.symbol).volume_min
        elif volume > mt5.symbol_info(strategy_event.symbol).volume_max:
            volume = mt5.symbol_info(strategy_event.symbol).volume_max

        self._create_and_put_sizing_event(strategy_event, volume)
