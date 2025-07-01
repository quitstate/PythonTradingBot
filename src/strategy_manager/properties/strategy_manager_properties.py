from pydantic import BaseModel


class BaseStrategyProps(BaseModel):
    pass


class MACrossoverProps(BaseStrategyProps):
    timeframe: str
    fast_period: int
    slow_period: int


class RSIProps(BaseStrategyProps):
    timeframe: str
    rsi_period: int
    rsi_upper: float
    rsi_lower: float
    sl_points: int
    tp_points: int
