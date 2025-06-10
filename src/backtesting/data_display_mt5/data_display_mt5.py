import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Dict, Any


class DataDisplayMT5:

    def __init__(self, trade_log_df: pd.DataFrame, initial_balance: float):
        if not isinstance(trade_log_df, pd.DataFrame):
            raise ValueError("trade_log_df must be a pandas DataFrame.")
        if trade_log_df.empty:
            raise ValueError("The trade_log_df DataFrame cannot be empty.")

        self.trade_log = trade_log_df.copy()
        self.initial_balance = initial_balance

        if 'entry_time' in self.trade_log.columns:
            self.trade_log['entry_time'] = pd.to_datetime(self.trade_log['entry_time'])
        if 'exit_time' in self.trade_log.columns:
            self.trade_log['exit_time'] = pd.to_datetime(self.trade_log['exit_time'])

        if 'profit' in self.trade_log.columns:
            self.trade_log['equity_after_trade'] = self.initial_balance + self.trade_log['profit'].cumsum()
            # Calculate drawdown for metrics and charts
            equity_curve = self.trade_log['equity_after_trade']
            self.trade_log['peak_equity'] = equity_curve.cummax()
            self.trade_log['drawdown_dollars'] = equity_curve - self.trade_log['peak_equity']
            self.trade_log['drawdown_percent'] = (
                self.trade_log['drawdown_dollars'] / self.trade_log['peak_equity']
            ) * 100

    def plot_equity_curve_and_trades(self, title: str = "Equity Curve with Trades") -> None:
        """Displays the equity curve chart."""
        if 'equity_after_trade' not in self.trade_log.columns or 'exit_time' not in self.trade_log.columns:
            print(
                "Cannot plot equity curve: "
                "missing 'equity_after_trade' or 'exit_time' columns."
            )
            return

        plt.figure(figsize=(12, 6))
        plt.plot(self.trade_log['exit_time'], self.trade_log['equity_after_trade'], label="Equidad")

        winning_trades = self.trade_log[self.trade_log['profit'] > 0]
        losing_trades = self.trade_log[self.trade_log['profit'] <= 0]

        plt.scatter(winning_trades['exit_time'], winning_trades['equity_after_trade'],
                    color='green', marker='^', label='Winning Trades', s=50, zorder=2)
        plt.scatter(losing_trades['exit_time'], losing_trades['equity_after_trade'],
                    color='red', marker='v', label='Losing/Neutral Trades', s=50, zorder=2)

        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel("Equity")
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def plot_win_loss_trades_bar_chart(self, title: str = "Winning vs. Losing Trades") -> None:
        """Displays a bar chart of the number of winning and losing trades."""
        metrics = self.calculate_metrics()
        if "Winning Trades" not in metrics or "Losing Trades" not in metrics:
            print(
                "Cannot plot trade count: "
                "missing 'Winning Trades' or 'Losing Trades' metrics."
            )
            return

        labels = ['Winning', 'Losing/Neutral']
        counts = [metrics["Winning Trades"], metrics["Losing Trades"]]

        plt.figure(figsize=(8, 6))
        bars = plt.bar(labels, counts, color=['green', 'red'])
        plt.title(title)
        plt.xlabel("Trade Type")
        plt.ylabel("Number of Trades")
        plt.grid(axis='y', linestyle='--')
        for bar in bars:
            yval = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width()/2.0,
                yval + 0.05 * max(counts),
                int(yval),
                ha='center',
                va='bottom'
            )
        plt.tight_layout()
        plt.show()

    def plot_drawdown_curve(self, title: str = "Drawdown Curve ($)") -> None:
        """Displays the drawdown curve chart in the account currency."""
        if 'drawdown_dollars' not in self.trade_log.columns or 'exit_time' not in self.trade_log.columns:
            print(
                "Cannot plot drawdown curve: "
                "missing 'drawdown_dollars' or 'exit_time' columns."
            )
            return
        plt.figure(figsize=(12, 6))
        plt.plot(
            self.trade_log['exit_time'],
            self.trade_log['drawdown_dollars'],
            label="Drawdown ($)",
            color='red'
        )
        plt.fill_between(
            self.trade_log['exit_time'],
            self.trade_log['drawdown_dollars'],
            0,
            color='red',
            alpha=0.3
        )
        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel("Drawdown ($)")
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculates and returns a dictionary of performance metrics."""
        if 'profit' not in self.trade_log.columns:
            print("Cannot calculate metrics: 'profit' column is missing.")
            return {}

        metrics = {}
        df = self.trade_log
        metrics["Total Trades"] = len(df)
        if metrics["Total Trades"] == 0:
            return {"Message": "No trades were executed."}

        metrics["Total Profit/Loss"] = df['profit'].sum()
        metrics["Gross Profit"] = df[df['profit'] > 0]['profit'].sum()
        metrics["Gross Loss"] = df[df['profit'] < 0]['profit'].sum()

        winning_trades = df[df['profit'] > 0]
        losing_trades = df[df['profit'] < 0]

        metrics["Winning Trades"] = len(winning_trades)
        metrics["Losing Trades"] = len(losing_trades)

        metrics["Win Rate (%)"] = (
            (metrics["Winning Trades"] / metrics["Total Trades"]) * 100
            if metrics["Total Trades"] > 0 else 0
        )

        metrics["Average Win ($)"] = winning_trades['profit'].mean() if not winning_trades.empty else 0
        metrics["Average Loss ($)"] = losing_trades['profit'].mean() if not losing_trades.empty else 0

        metrics["Profit Factor"] = (
            abs(metrics["Gross Profit"] / metrics["Gross Loss"])
            if metrics["Gross Loss"] != 0 else np.inf
        )

        # Drawdown
        if 'drawdown_dollars' in df.columns and 'drawdown_percent' in df.columns:
            metrics["Max Drawdown ($)"] = df['drawdown_dollars'].min()
            metrics["Max Drawdown (%)"] = abs(df['drawdown_percent'].min())
        else:
            metrics["Max Drawdown (%)"] = "N/A (equity_after_trade not available)"

        if 'profit' in df.columns and len(df['profit']) > 1:
            returns = df['profit'] / self.initial_balance
            if returns.std() != 0:
                sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)
            else:
                sharpe_ratio = 0
            metrics["Sharpe Ratio (simplificado)"] = sharpe_ratio
        else:
            metrics["Sharpe Ratio (simplificado)"] = "N/A"

        return metrics

    def display_summary(self) -> None:
        """Prints a summary of the performance metrics."""
        metrics = self.calculate_metrics()
        print("\n--- Backtest Summary ---")
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")
        print("---------------------------\n")
