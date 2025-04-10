from enum import Enum
from pydantic import BaseModel
import pandas as pd


class EventType(str, Enum):
    DATA = "DATA"
    SIGNAL = "SIGNAL"
    SIZING = "SIZING"


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class BaseEvent(BaseModel):
    event_type: EventType

    class Config:
        # use_enum_values = True
        arbitrary_types_allowed = True


class DataEvent(BaseEvent):
    event_type: EventType = EventType.DATA
    symbol: str
    data: pd.Series


class SignalEvent(BaseEvent):
    event_type: EventType = EventType.SIGNAL
    symbol: str
    signal: SignalType
    target_order: OrderType
    target_price: float
    magic_number: int
    stop_loss: float
    take_profit: float


class SizingEvent(BaseEvent):
    event_type: EventType = EventType.SIZING
    symbol: str
    signal: SignalType
    target_order: OrderType
    target_price: float
    magic_number: int
    stop_loss: float
    take_profit: float
    volume: float
