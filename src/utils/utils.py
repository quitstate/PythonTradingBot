import MetaTrader5 as mt5


class Utils():

    def __init__(self):
        pass

    @staticmethod
    def convert_currency_amount_to_another_currency(
        amount: float, from_currency: str, to_currency: str
    ) -> float:

        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency == to_currency:
            return amount

        all_forex_symbol = (
            "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD", "CADCHF", "CADJPY", "CHFJPY",
            "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD", "GBPCAD", "GBPCHF",
            "GBPJPY", "GBPNZD", "GBPUSD", "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD", "USDCAD",
            "USDCHF", "USDJPY"
        )

        forex_symbol = [
            symbol for symbol in all_forex_symbol
            if from_currency in symbol and to_currency in symbol
        ][0]
        forex_symbol_base = forex_symbol[:3]

        tick = mt5.symbol_info_tick(forex_symbol)

        if tick is None:
            raise ValueError(f"Tick for {forex_symbol} not found.")

        last_price = tick.bid

        converted_amount = amount / last_price if forex_symbol_base == to_currency else amount * last_price
        return converted_amount
