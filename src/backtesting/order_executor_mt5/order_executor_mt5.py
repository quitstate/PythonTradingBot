import uuid
from queue import Queue
from events.events import OrderEvent, ExecutionEvent, PlacedPendingOrderEvent, StrategyType, OrderType
import pandas as pd


class BacktestOrderExecutor:
    def __init__(self, platform_connector, events_queue: Queue, data_source, portfolio):
        self.platform = platform_connector
        self.events_queue = events_queue
        self.data_source = data_source
        self.portfolio = portfolio
        self.trade_log = []

    def execute_order(self, order_event: OrderEvent):
        symbol = order_event.symbol
        order_strategy_type = order_event.strategy
        side = order_strategy_type.value.lower()
        volume = order_event.volume
        order_type_enum = order_event.target_order

        latest_tick = self.data_source.get_latest_tick(symbol)
        current_time = pd.to_datetime(latest_tick['time_msc'], unit='ms')

        if order_type_enum == OrderType.MARKET:
            price_to_execute_at = latest_tick['ask'] if side == 'buy' else latest_tick['bid']

            ticket = str(uuid.uuid4())
            position_dict = {
                "ticket": ticket, "symbol": symbol, "side": side,
                "volume": volume, "entry_price": price_to_execute_at,
                "timestamp": current_time, "magic": order_event.magic_number,
                "sl": order_event.stop_loss, "tp": order_event.take_profit
            }
            self.platform.add_position(position_dict)

            exec_event = ExecutionEvent(
                symbol=symbol, strategy=order_strategy_type,
                fill_price=price_to_execute_at, fill_time=current_time,
                volume=volume
            )
            self.events_queue.put(exec_event)
            print(f"BACKTEST EXEC: Market {side} {volume} {symbol} @ {price_to_execute_at} at {current_time}")

        elif order_type_enum in [OrderType.LIMIT, OrderType.STOP]:
            placed_event = PlacedPendingOrderEvent(
                symbol=symbol, strategy=order_strategy_type,
                target_order=order_type_enum, target_price=order_event.target_price,
                magic_number=order_event.magic_number, stop_loss=order_event.stop_loss,
                take_profit=order_event.take_profit, volume=order_event.volume
            )
            self.events_queue.put(placed_event)
            print(
                f"BACKTEST EXEC: Placed Pending {order_type_enum.value} {side} "
                f"{volume} {symbol} @ {order_event.target_price}"
            )
        else:
            print(f"BACKTEST EXEC: Unknown order type {order_type_enum} in OrderEvent")

    def _calculate_pnl(self, position_dict: dict, exit_price: float) -> float:
        direction = 1 if position_dict["side"] == "buy" else -1
        price_diff = exit_price - position_dict["entry_price"]
        pnl = direction * price_diff * position_dict["volume"] * 100000
        return pnl

    def close_position_by_ticket(self, ticket: str):
        position_to_close = None
        open_positions = self.platform.get_open_positions()
        for pos in open_positions:
            if pos['ticket'] == ticket:
                position_to_close = pos
                break

        if not position_to_close:
            print(f"BACKTEST CLOSE: Position with ticket {ticket} not found to close.")
            return

        latest_tick = self.data_source.get_latest_tick(position_to_close['symbol'])
        exit_price = (
            latest_tick['bid'] if position_to_close['side'] == 'buy'
            else latest_tick['ask']
        )
        exit_time = pd.to_datetime(latest_tick['time_msc'], unit='ms')

        pnl = self._calculate_pnl(position_to_close, exit_price)
        self.platform.balance += pnl
        self.platform.update_equity(self.platform.get_balance())
        self.platform.close_position(ticket)

        self.trade_log.append({
            "ticket": ticket, "symbol": position_to_close['symbol'],
            "open_side": position_to_close['side'], "entry_price": position_to_close['entry_price'],
            "entry_time": position_to_close['timestamp'], "volume": position_to_close['volume'],
            "close_side": "sell" if position_to_close['side'] == "buy" else "buy",
            "exit_price": exit_price, "exit_time": exit_time,
            "profit": pnl, "magic": position_to_close.get('magic', 0),
            "sl": position_to_close.get('sl', 0), "tp": position_to_close.get('tp', 0)
        })

        close_strategy_type = StrategyType.SELL if position_to_close['side'] == 'buy' else StrategyType.BUY
        exec_event_close = ExecutionEvent(
            symbol=position_to_close['symbol'], strategy=close_strategy_type,
            fill_price=exit_price, fill_time=exit_time,
            volume=position_to_close['volume']
        )
        self.events_queue.put(exec_event_close)
        print(
            f"BACKTEST CLOSE: Closed {position_to_close['side']} {ticket} "
            f"for {position_to_close['symbol']} @ {exit_price}, "
            f"PnL: {pnl:.2f}"
        )

    def close_strategy_positions_by_symbol(self, symbol: str, side_to_close: str = None):
        """
        Closes positions for a given symbol and strategy magic number.
        Optionally filters by side ('buy' or 'sell').
        """
        positions_to_check = list(
            self.portfolio.get_strategy_open_positions()
        )

        closed_any = False
        for pos_info in positions_to_check:
            if pos_info.symbol == symbol:
                current_pos_side_is_buy = (pos_info.type == 0)

                should_close = False
                if side_to_close == 'buy' and current_pos_side_is_buy:
                    should_close = True
                elif side_to_close == 'sell' and not current_pos_side_is_buy:
                    should_close = True
                elif side_to_close is None:
                    should_close = True

                if should_close:
                    print(
                        f"BACKTEST CLOSE_STRATEGY: Attempting to close position ticket {pos_info.ticket} "
                        f"for {symbol}"
                    )
                    self.close_position_by_ticket(pos_info.ticket)
                    closed_any = True
        if not closed_any:
            print(
                f"BACKTEST CLOSE_STRATEGY: No matching {side_to_close or 'any'} positions found "
                f"for symbol {symbol} with magic {self.portfolio.magic}"
            )

    def close_strategy_long_positions_by_symbol(self, symbol: str):
        self.close_strategy_positions_by_symbol(symbol, side_to_close='buy')

    def close_strategy_short_positions_by_symbol(self, symbol: str):
        self.close_strategy_positions_by_symbol(symbol, side_to_close='sell')

    def get_open_orders(self):
        return self.platform.get_open_positions()

    def get_trade_log(self):
        return self.trade_log
