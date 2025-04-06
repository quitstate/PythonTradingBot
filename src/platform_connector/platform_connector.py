import MetaTrader5 as mt5
import os
from dotenv import load_dotenv, find_dotenv


class PlatformConnector():
    def __init__(self, symbol_list: list) -> None:

        # Load environment variables from .env file
        load_dotenv(find_dotenv())

        # Initialize MetaTrader 5 platform
        self._initialize_platform()

        # Display a warning message if the account is a live account
        self._live_account_warning()

        # Print account information
        self.__print_account_info()

        # Check if algorithmic trading is enabled in MetaTrader 5
        self._check_algo_trading_enabled()

        # Add symbols to the Market Watch window
        self._add_symbols_to_marketwatch(symbol_list)

    def _initialize_platform(self) -> None:
        """
        Initialize MetaTrader 5 platform with environment variables

        Raises:
            Exception: If MetaTrader 5 initialization fails

        Returns:
            None
        """
        print("Initializing MetaTrader 5...")
        if mt5.initialize(
            path=os.getenv("MT5_PATH"),
            login=int(os.getenv("MT5_LOGIN")),
            password=os.getenv("MT5_PASSWORD"),
            server=os.getenv("MT5_SERVER"),
            timeout=int(os.getenv("MT5_TIMEOUT")),
            portable=eval(os.getenv("MT5_PORTABLE")),
        ):
            print("MetaTrader 5 initialized successfully.")
        else:
            raise Exception("Failed to initialize MetaTrader 5. Error code:",
                  mt5.last_error())

    def _live_account_warning(self) -> None:
        """
        Display a warning message if the account is a live account.

        Returns:
            None
        """
        account_info = mt5.account_info()

        if account_info.trade_mode == mt5.ACCOUNT_TRADE_MODE_REAL:
            print(
                "Warning: You are using a live account. "
                "Proceed with caution."
            )
        elif account_info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO:
            print("You are using a demo account. ")
        else:
            print("You are using a different type of account. ")

    def _check_algo_trading_enabled(self) -> None:
        """
        Check if algorithmic trading is enabled in MetaTrader 5.
        """
        if not mt5.terminal_info().trade_allowed:
            raise Exception(
                (
                    "Algorithmic trading is desactivated. Please enable it in "
                    "the MetaTrader 5 terminal."
                )
            )

    def _add_symbols_to_marketwatch(self, symbols: list) -> None:
        """
        Add symbols to the Market Watch window.

        Args:
            symbols (list): List of symbols to add.

        Returns:
            None
        """
        for symbol in symbols:
            if mt5.symbol_info(symbol) is None:
                print(
                    f"{symbol} not found. "
                    f"Please check if the symbol exist. "
                    f"Error code: {mt5.last_error()}"
                )
                continue

            if not mt5.symbol_info(symbol).visible:
                if not mt5.symbol_select(symbol, True):
                    print(
                        f"Failed to add {symbol} to Market Watch. "
                        f"Error code: {mt5.last_error()}"
                    )
                else:
                    print(f"{symbol} added to Market Watch.")
            else:
                print(f"{symbol} is already in Market Watch.")

    def __print_account_info(self) -> None:
        """
        Print account information.

        Returns:
            None
        """
        account_info = mt5.account_info()._asdict()
        print("+-------Account Information -------+")
        print(f"| - Account Number: {account_info['login']}")
        print(f"| - Account Name: {account_info['name']}")
        print(f"| - Broker: {account_info['company']}")
        print(f"| - Server: {account_info['server']}")
        print(f"| - Leverage: {account_info['leverage']}")
        print(f"| - Account Currency: {account_info['currency']}")
        print(f"| - Account Balance: {account_info['balance']}")
        print("+-----------------------------------+")
