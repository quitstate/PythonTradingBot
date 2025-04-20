from events.events import SizingEvent
from ..interfaces.risk_manager_interface import IRiskManager
from ..properties.risk_manager_properties import MaxLeverageFactorRiskProps
import MetaTrader5 as mt5
import sys


class MaxLeverageFactorRiskManager(IRiskManager):
    """
    Risk manager that checks if the leverage factor is within the specified limits.
    """

    def __init__(self, properties: MaxLeverageFactorRiskProps):
        self.max_leverage_factor = properties.max_leverage_factor

    def _compute_leverage_factor(self, account_value_account_currency: float) -> float:

        account_equity = mt5.account_info().equity
        if account_equity <= 0:
            return sys.float_info.max
        leverage_factor = account_value_account_currency / account_equity
        return leverage_factor

    def _check_expected_new_position_is_compliant_with_max_leverage_factor(
        self,
        sizing_event: SizingEvent,
        current_position_value_account_currency: float,
        new_position_value_account_currency: float
    ) -> bool:
        """
        Check if the expected new position is compliant with the max leverage factor.
        """
        new_account_value = current_position_value_account_currency + new_position_value_account_currency

        new_leverage_factor = self._compute_leverage_factor(new_account_value)

        if abs(new_leverage_factor) <= self.max_leverage_factor:
            return True
        else:
            print(
                (
                    f"The objetive position {sizing_event.signal} {sizing_event.volume}",
                    f"New leverage factor {abs(new_leverage_factor)} exceeds "
                    f"max leverage factor {self.max_leverage_factor}."
                )
            )
            return False

    def assess_order(
        self,
        sizing_event: SizingEvent,
        current_position_value_account_currency: float,
        new_position_value_account_currency: float
    ) -> float | None:

        if self._check_expected_new_position_is_compliant_with_max_leverage_factor(
            sizing_event,
            current_position_value_account_currency,
            new_position_value_account_currency
        ):
            return sizing_event.volume
        else:
            return 0.0
