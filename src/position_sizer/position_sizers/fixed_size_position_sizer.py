from events.events import StrategyEvent
from data_source.data_source import DataSource
from ..interfaces.position_sizer_interface import IPositionSizer
from ..properties.position_sizer_properties import FixedSizingProps


class FixedSizePositionSizer(IPositionSizer):

    def __init__(self, properties: FixedSizingProps):
        self.fixed_volume = properties.volume

    def size_strategy(self, strategy_event: StrategyEvent, data_source: DataSource) -> float:
        if self.fixed_volume <= 0.0:
            raise ValueError("Fixed volume must be greater than 0")
        return self.fixed_volume
