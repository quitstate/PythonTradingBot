from events.events import StrategyEvent
from data_source.data_source import DataSource
from ..interfaces.position_sizer_interface import IPositionSizer
from ..properties.position_sizer_properties import RiskPctSizingProps
from utils.utils import Utils
import MetaTrader5 as mt5


class RiskPctPositionSizer(IPositionSizer):

    def __init__(self, properties: RiskPctSizingProps):
        self.risk_pct = properties.risk_pct

    def size_strategy(self, strategy_event: StrategyEvent, data_source: DataSource) -> float:

        if self.risk_pct <= 0.0:
            raise ValueError("Risk percentage must be greater than 0.")

        if strategy_event.stop_loss <= 0.0:
            raise ValueError("Stop loss must be greater than 0.")

        account_info = mt5.account_info()
        if account_info is None:
            raise ValueError("Failed to retrieve account information.")

        symbol_info = mt5.symbol_info(strategy_event.symbol)

        if strategy_event.target_order == "MARKET":
            last_tick = data_source.get_latest_tick(strategy_event.symbol)
            entry_price = last_tick['ask'] if strategy_event.strategy == "BUY" else last_tick['bid']
        else:
            entry_price = strategy_event.target_price

        equity = account_info.equity
        volume_step = symbol_info.volume_step
        tick_size = symbol_info.trade_tick_size
        account_currency = account_info.currency
        symbol_profit_currency = symbol_info.currency_profit
        contract_size = symbol_info.trade_contract_size

        tick_value_prifit_currency = contract_size * tick_size

        tick_value_account_currency = Utils.convert_currency_amount_to_another_currency(
            tick_value_prifit_currency, symbol_profit_currency, account_currency
        )

        try:
            price_distance_in_integer_ticksizes = int(abs(entry_price - strategy_event.stop_loss) / tick_size)
            monetary_risk = equity * self.risk_pct
            volume = monetary_risk / (price_distance_in_integer_ticksizes * tick_value_account_currency)
            volume = round(volume / volume_step) * volume_step

        except ZeroDivisionError:
            raise ValueError("Stop loss cannot be equal to entry price.")

        else:
            return volume
