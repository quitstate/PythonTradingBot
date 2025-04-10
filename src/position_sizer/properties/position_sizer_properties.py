from pydantic import BaseModel


class BaseSizingProps(BaseModel):
    pass


class MinSizingProps(BaseSizingProps):
    pass


class FixedSizingProps(BaseSizingProps):
    volume: float


class RiskPctSizingProps(BaseSizingProps):
    risk_pct: float
