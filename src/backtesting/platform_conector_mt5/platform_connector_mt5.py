class BacktestPlatformConnector:
    def __init__(self, initial_balance=100000.0, leverage=5):
        self.balance = initial_balance
        self.equity = initial_balance
        self.leverage = leverage
        self.positions = []

    def get_balance(self):
        return self.balance

    def get_equity(self):
        return self.equity

    def get_leverage(self):
        return self.leverage

    def get_open_positions(self):
        return self.positions

    def update_equity(self, new_equity):
        self.equity = new_equity

    def add_position(self, position):
        self.positions.append(position)

    def close_position(self, ticket):
        self.positions = [p for p in self.positions if p["ticket"] != ticket]
