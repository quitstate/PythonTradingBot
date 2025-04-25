from .interfaces.risk_manager_interface import IRiskManager
from data_provider.data_provider import DataProvider
from portfolio.portfolio import Portfolio
from .properties.risk_manager_properties import BaseRiskProps, MaxLeverageFactorRiskProps
from .risk_managers.max_leverage_factor_risk_manager import MaxLeverageFactorRiskManager
from events.events import SizingEvent, OrderEvent
from utils.utils import Utils
import MetaTrader5 as mt5

from queue import Queue


class RiskManager(IRiskManager):
    """
    Risk Manager class that implements the IRiskManager interface.
    This class is responsible for managing risk in the trading system.
    """
    def __init__(
        self,
        events_queue: Queue,
        data_provider: DataProvider,
        portfolio: Portfolio,
        risk_properties: BaseRiskProps
    ):
        """
        Initialize the RiskManager with the given configuration.
        """
        self.events_queue = events_queue
        self.DATA_PROVIDER = data_provider
        self.PORTFOLIO = portfolio
        self.risk_management_method = self._get_risk_management_method(risk_properties)

    def _get_risk_management_method(self, risk_props: BaseRiskProps) -> IRiskManager:
        """
        Get the risk management method based on the provided properties.
        """
        if isinstance(risk_props, MaxLeverageFactorRiskProps):
            return MaxLeverageFactorRiskManager(risk_props)

        else:
            raise NotImplementedError(f"Risk management method for {type(risk_props)} is not implemented.")

    def _compute_current_value_of_position_in_account_currency(self) -> float:
        """
        Compute the current value of the position in the account currency.
        """
        current_positions = self.PORTFOLIO.get_strategy_open_positions()

        total_value = 0.0

        print(current_positions)

        for position in current_positions:
            total_value += self._compute_value_of_position_in_account_currency(
                position.symbol, position.volume, position.type
            )

        return total_value

    def _compute_value_of_position_in_account_currency(
        self, symbol: str, volume: float, position_type: int
    ) -> float:
        """
        Compute the value of a position in the account currency.
        """
        symbol_info = mt5.symbol_info(symbol)
        trade_unit = volume * symbol_info.trade_contract_size

        value_traded_in_profit_currency = trade_unit * self.DATA_PROVIDER.get_latest_tick(symbol)['bid']

        value_traded_in_account_currency = Utils.convert_currency_amount_to_another_currency(
            value_traded_in_profit_currency,
            symbol_info.currency_profit,
            mt5.account_info().currency,
        )

        if position_type == mt5.ORDER_TYPE_BUY:
            return value_traded_in_account_currency
        elif position_type == mt5.ORDER_TYPE_SELL:
            return -value_traded_in_account_currency
        else:
            raise ValueError(f"Invalid position type: {position_type}. Expected ORDER_BUY or ORDER_SELL.")

    def _create_and_put_order_event(self, sizing_event: SizingEvent, volume: float) -> None:
        """
        Create and put an order event into the events queue.
        """
        order_event = OrderEvent(
            symbol=sizing_event.symbol,
            signal=sizing_event.signal,
            target_order=sizing_event.target_order,
            target_price=sizing_event.target_price,
            magic_number=sizing_event.magic_number,
            stop_loss=sizing_event.stop_loss,
            take_profit=sizing_event.take_profit,
            volume=volume,
        )
        self.events_queue.put(order_event)

    def assess_order(self, sizing_event: SizingEvent) -> None:

        current_position_value = self._compute_current_value_of_position_in_account_currency()

        position_type = mt5.ORDER_TYPE_BUY if sizing_event.signal == 'BUY' else mt5.ORDER_TYPE_SELL

        new_position_value = self._compute_value_of_position_in_account_currency(
            sizing_event.symbol,
            sizing_event.volume,
            position_type
        )

        new_volume = self.risk_management_method.assess_order(
            sizing_event, current_position_value, new_position_value
        )

        if new_volume > 0.0:
            self._create_and_put_order_event(sizing_event, new_volume)
        else:
            print(f"Risk management rejected the order for {sizing_event.symbol} with volume {new_volume}.")
