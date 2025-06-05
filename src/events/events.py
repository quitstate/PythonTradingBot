from enum import Enum
from pydantic import BaseModel
import pandas as pd
from datetime import datetime


class EventType(str, Enum):
    DATA = "DATA"
    STRATEGY = "STRATEGY"
    SIZING = "SIZING"
    ORDER = "ORDER"
    EXECUTION = "EXECUTION"
    PENDING = "PENDING"


class StrategyType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class BaseEvent(BaseModel):
    event_type: EventType

    class Config:
        arbitrary_types_allowed = True


class DataEvent(BaseEvent):
    event_type: EventType = EventType.DATA
    symbol: str
    data: pd.Series


class StrategyEvent(BaseEvent):
    event_type: EventType = EventType.STRATEGY
    symbol: str
    strategy: StrategyType
    target_order: OrderType
    target_price: float
    magic_number: int
    stop_loss: float
    take_profit: float


class SizingEvent(BaseEvent):
    event_type: EventType = EventType.SIZING
    symbol: str
    strategy: StrategyType
    target_order: OrderType
    target_price: float
    magic_number: int
    stop_loss: float
    take_profit: float
    volume: float


class OrderEvent(BaseEvent):
    event_type: EventType = EventType.ORDER
    symbol: str
    strategy: StrategyType
    target_order: OrderType
    target_price: float
    magic_number: int
    stop_loss: float
    take_profit: float
    volume: float


class ExecutionEvent(BaseEvent):
    event_type: EventType = EventType.EXECUTION
    symbol: str
    strategy: StrategyType
    fill_price: float
    fill_time: datetime
    volume: float


class PlacedPendingOrderEvent(BaseEvent):
    event_type: EventType = EventType.PENDING
    symbol: str
    strategy: StrategyType
    target_order: OrderType
    target_price: float
    magic_number: int
    stop_loss: float
    take_profit: float
    volume: float
