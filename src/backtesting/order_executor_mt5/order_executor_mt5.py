import uuid


class BacktestOrderExecutor:
    def __init__(self, platform_connector):
        self.platform = platform_connector
        self.orders = []

    def execute_order(self, symbol, side, volume, price, timestamp):
        """Simula una orden ejecutada al precio dado"""

        ticket = str(uuid.uuid4())
        position = {
            "ticket": ticket,
            "symbol": symbol,
            "side": side,  # 'buy' or 'sell'
            "volume": volume,
            "entry_price": price,
            "timestamp": timestamp
        }
        self.platform.add_position(position)
        self.orders.append(position)
        return ticket

    def close_order(self, ticket, exit_price):
        """Cierra la posición simulando el cierre en exit_price"""
        position = next((o for o in self.orders if o["ticket"] == ticket), None)
        if not position:
            return

        pnl = self._calculate_pnl(position, exit_price)
        self.platform.balance += pnl
        self.platform.update_equity(self.platform.get_balance())
        self.platform.close_position(ticket)

    def _calculate_pnl(self, position, exit_price):
        """Calcula PnL en unidades monetarias, sin comisiones"""
        direction = 1 if position["side"] == "buy" else -1
        price_diff = exit_price - position["entry_price"]
        return direction * price_diff * position["volume"] * 100000  # 1 lote = 100k

    def get_open_orders(self):
        return self.orders
