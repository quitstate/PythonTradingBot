from events.events import SignalEvent
from data_provider.data_provider import DataProvider
from ..interfaces.position_sizer_interface import IPositionSizer
from ..properties.position_sizer_properties import FixedSizingProps


class FixedSizePositionSizer(IPositionSizer):

    def __init__(self, properties: FixedSizingProps):
        self.fixed_volume = properties.volume

    def size_signal(self, signal_event: SignalEvent, data_provider: DataProvider) -> float:
        if self.fixed_volume <= 0.0:
            raise ValueError("Fixed volume must be greater than 0")
        return self.fixed_volume
