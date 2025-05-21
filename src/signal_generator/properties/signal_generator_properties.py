from pydantic import BaseModel


class BaseSignalProps(BaseModel):
    pass


class MACrossoverProps(BaseSignalProps):
    timeframe: str
    fast_period: int
    slow_period: int


class RSIProps(BaseSignalProps):
    timeframe: str
    rsi_period: int
    rsi_upper: float
    rsi_lower: float
    sl_points: int
    tp_points: int
