from portfolio.portfolio import Portfolio
from queue import Queue
from events.events import OrderEvent, ExecutionEvent, PlacedPendingOrderEvent, SignalType
from datetime import datetime
from utils.utils import Utils
import pandas as pd
import time
import MetaTrader5 as mt5


class OrderExecutor():

    def __init__(self, events_queue: Queue, portfolio: Portfolio):
        self.events_queue = events_queue
        self.PORTFOLIO = portfolio

    def execute_order(self, order_event: OrderEvent) -> None:
        """
        Execute the order by sending it to the broker.
        """

        if order_event.target_order == "MARKET":
            self._execute_market_order(order_event)
        else:
            self._send_pending_order(order_event)

    def _execute_market_order(self, order_event: OrderEvent) -> None:
        """
        Execute the market order by sending it to the broker.
        """
        if order_event.signal == "BUY":
            order_type = mt5.ORDER_TYPE_BUY
        elif order_event.signal == "SELL":
            order_type = mt5.ORDER_TYPE_SELL
        else:
            raise ValueError("Invalid order type. Must be 'BUY' or 'SELL'.")

        market_order_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": order_event.symbol,
            "volume": order_event.volume,
            "sl": order_event.stop_loss,
            "tp": order_event.take_profit,
            "type": order_type,
            "deviation": 0,
            "magic": order_event.magic_number,
            "comment": "FWK Market Order",
            "type_filling": mt5.ORDER_FILLING_IOC,
            'price': mt5.symbol_info(order_event.symbol).bid
            }

        result = mt5.order_send(market_order_request)

        if self._check_execution_status(result):
            print(
                f"Market order executed successfully. {order_event.signal} for {order_event.symbol} "
                f"at {result.price} with {result.volume} volume"
            )
            self._create_and_put_execution_event(result)

        else:
            print(
                f"Market order execution failed. {order_event.signal} for "
                f"{order_event.symbol}: {result.comment}"
            )

    def _send_pending_order(self, order_event: OrderEvent) -> None:
        """
        Send a pending order to the broker.
        """
        if order_event.target_order == "STOP":
            order_type = mt5.ORDER_BUY_STOP if order_event.signal == "BUY" else mt5.ORDER_SELL_STOP
        elif order_event.target_order == "LIMIT":
            order_type = mt5.ORDER_BUY_LIMIT if order_event.signal == "BUY" else mt5.ORDER_SELL_LIMIT
        else:
            raise Exception(f"ORD EXEC: the pending order {order_event.target_order} is not valid")

        pending_order_request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": order_event.symbol,
            "volume": order_event.volume,
            "sl": order_event.stop_loss,
            "tp": order_event.take_profit,
            "type": order_type,
            "deviation": 0,
            "magic": order_event.magic_number,
            "comment": "FWK Pending Order",
            "type_filling": mt5.ORDER_FILLING_IOC,
            "price": order_event.target_price,
            "type_time": mt5.ORDER_TIME_GTC,
        }

        result = mt5.order_send(pending_order_request)

        if self._check_execution_status(result):
            print(
                f"Pending order executed successfully. {order_event.signal} {order_event.target_order} "
                f"for {order_event.symbol} at {order_event.target_price} with {order_event.volume} volume"
            )
            self._create_and_put_placed_pending_order_event(order_event)

        else:
            print(
                f"Pending order execution failed. {order_event.signal} for "
                f"{order_event.symbol}: {result.comment}"
            )

    def cancel_pending_order_by_ticket(self, ticket: int) -> None:
        """
        Cancel a pending order by its ticket number.

        Args:
            ticket (int): The ticket number of the pending order to cancel.

        Returns:
            None
        """

        pending_order = mt5.orders_get(ticket=ticket)[0]

        if pending_order is None:
            print(f"ORD EXEC: Pending order with ticket {ticket} not found.")
            return

        cancel_request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": pending_order.ticket,
            "symbol": pending_order.symbol,
            "comment": "FWK Cancel Pending Order",
        }

        result = mt5.order_send(cancel_request)

        if self._check_execution_status(result):
            print(
                f"Pending order with ticket {ticket} in {pending_order.symbol} "
                f"and volume {pending_order.volume_initial} cancelled successfully."
            )
        else:
            print(f"Failed to cancel pending order {ticket} in {pending_order.symbol}: {result.comment}")

    def close_position_by_ticket(self, ticket: int) -> None:
        """
        Close a position by its ticket number.

        Args:
            ticket (int): The ticket number of the position to close.

        Returns:
            None
        """

        position = mt5.positions_get(ticket=ticket)[0]

        if position is None:
            print(f"ORD EXEC: Position with ticket {ticket} not found.")
            return

        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": position.ticket,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": mt5.ORDER_TYPE_BUY if position.type == mt5.ORDER_TYPE_SELL else mt5.ORDER_TYPE_SELL,
            "comment": "FWK Close Position",
            "type_filling": mt5.ORDER_FILLING_IOC
        }

        result = mt5.order_send(close_request)

        if self._check_execution_status(result):
            print(
                f"Position with ticket {ticket} in {position.symbol} "
                f"and volume {position.volume} closed successfully."
            )
        else:
            print(f"Failed to close position {ticket} in {position.symbol}: {result.comment}")

    def close_strategy_long_positions_by_symbol(self, symbol: str) -> None:
        """
        Close all long positions for a given symbol.

        Args:
            symbol (str): The symbol for which to close long positions.

        Returns:
            None
        """

        positions = self.PORTFOLIO.get_strategy_open_positions()

        if positions is None:
            print(f"ORD EXEC: No positions found for symbol {symbol}.")
            return

        for position in positions:
            if position.symbol == symbol and position.type == mt5.ORDER_TYPE_BUY:
                self.close_position_by_ticket(position.ticket)

    def close_strategy_short_positions_by_symbol(self, symbol: str) -> None:
        """
        Close all short positions for a given symbol.

        Args:
            symbol (str): The symbol for which to close short positions.

        Returns:
            None
        """

        positions = self.PORTFOLIO.get_strategy_open_positions()

        if positions is None:
            print(f"ORD EXEC: No positions found for symbol {symbol}.")
            return

        for position in positions:
            if position.symbol == symbol and position.type == mt5.ORDER_TYPE_SELL:
                self.close_position_by_ticket(position.ticket)

    def _create_and_put_placed_pending_order_event(self, order_event: OrderEvent) -> None:
        """
        Creates a pending order event based on the order event and puts it into the events queue.

        Args:
            order_event (OrderEvent): The order event to be processed.

        Returns:
            None
        """
        placed_pending_order_event = PlacedPendingOrderEvent(
            symbol=order_event.symbol,
            signal=order_event.signal,
            target_order=order_event.target_order,
            target_price=order_event.target_price,
            magic_number=order_event.magic_number,
            stop_loss=order_event.stop_loss,
            take_profit=order_event.take_profit,
            volume=order_event.volume
        )

        # Place the pending order event into the events queue
        self.events_queue.put(placed_pending_order_event)

    def _create_and_put_execution_event(self, order_result) -> None:
        """
        Creates an execution event based on the order result and puts it into the events queue.

        Args:
            order_result (OrderResult): The result of the order execution.

        Returns:
            None
        """
        # We obtain the deal information resulting from the order execution
        # using the POSITION to which the deal belongs
        # (instead of the deal's own ticket),
        # because in LIVE the deal result is often 0 if queried immediately.
        # deal = mt5.history_deals_get(ticket=order_result.deal)[0]
        deal = None

        # We simulate a fill_time using the current moment
        fill_time = datetime.now()

        # We create a small loop to give the server time to generate the deal.
        # Define a maximum of 5 attempts.
        for _ in range(5):
            # Wait for 0.5 seconds
            time.sleep(0.5)
            try:
                deal = mt5.history_deals_get(
                    position=order_result.order
                )[0]  # Use position instead of ticket
            except IndexError:
                deal = None

            if not deal:
                # If we do not obtain the deal, we save the fill time as "now"
                # to have an approximation -> you can modify it if necessary
                fill_time = datetime.now()
                continue
            else:
                break

        # If after the loop we have not obtained the deal, display an error message
        if not deal:
            print(
                f"{Utils.dateprint()} - ORD EXEC: Unable to obtain the deal for the execution of the order"
                f"{order_result.order}, although it was probably executed."
            )

        # Create the execution event
        execution_event = ExecutionEvent(
            symbol=order_result.request.symbol,
            signal=SignalType.BUY if order_result.request.type == mt5.DEAL_TYPE_BUY else SignalType.SELL,
            fill_price=order_result.price,
            fill_time=fill_time if not deal else pd.to_datetime(deal.time_msc, unit='ms'),
            volume=order_result.request.volume
        )

        # Place the execution event into the events queue
        self.events_queue.put(execution_event)

    def _check_execution_status(self, order_result) -> bool:
        """
        Check the execution status of the order.
        """
        if order_result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"Order executed successfully: {order_result.retcode}")
            return True
        elif order_result.retcode == mt5.TRADE_RETCODE_DONE_PARTIAL:
            print(f"Order executed successfully: {order_result.retcode}")
            return True
        else:
            print(f"Order execution failed: {order_result.retcode}")
            return False
