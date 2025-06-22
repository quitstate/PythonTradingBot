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

        # Convertir columnas de tiempo si existen, manejando posibles errores o NaT
        if 'entry_time' in self.trade_log.columns:
            self.trade_log['entry_time'] = pd.to_datetime(self.trade_log['entry_time'], errors='coerce')
        if 'exit_time' in self.trade_log.columns:
            self.trade_log['exit_time'] = pd.to_datetime(self.trade_log['exit_time'], errors='coerce')

        # Crear un DataFrame solo con trades ejecutados para cálculos de rendimiento y
        # plots de equidad/drawdown
        self.executed_trades_log = self.trade_log[self.trade_log['profit'].notna()].copy()

        if not self.executed_trades_log.empty and 'profit' in self.executed_trades_log.columns:
            # Asegurar que exit_time en executed_trades_log es datetime y está ordenado para cumsum
            if 'exit_time' in self.executed_trades_log.columns:
                self.executed_trades_log['exit_time'] = pd.to_datetime(self.executed_trades_log['exit_time'])
                # Solo ordenar si no hay NaT, o manejarlos.
                if not self.executed_trades_log['exit_time'].isna().any():
                    self.executed_trades_log.sort_values(by='exit_time', inplace=True)
                else:
                    print(
                        "Advertencia: Hay NaT en 'exit_time' para trades ejecutados; "
                        "la curva de equidad podría no ser precisa."
                    )

            self.executed_trades_log['equity_after_trade'] = (
                self.initial_balance + self.executed_trades_log['profit'].cumsum()
            )
            equity_curve = self.executed_trades_log[
                'equity_after_trade'
            ]
            self.executed_trades_log['peak_equity'] = equity_curve.cummax()
            self.executed_trades_log['drawdown_dollars'] = (
                equity_curve - self.executed_trades_log['peak_equity']
            )
            self.executed_trades_log['drawdown_percent'] = np.where(
                self.executed_trades_log['peak_equity'].fillna(0) != 0,  # Evitar división por cero/NaN
                (
                    self.executed_trades_log['drawdown_dollars']
                    / self.executed_trades_log['peak_equity']
                ) * 100,
                0.0  # O np.nan si se prefiere
            )
        else:
            # Si no hay trades ejecutados, inicializar executed_trades_log con columnas esperadas
            expected_cols = [
                'entry_time', 'exit_time', 'profit', 'equity_after_trade',
                'peak_equity', 'drawdown_dollars', 'drawdown_percent'
            ]
            self.executed_trades_log = pd.DataFrame(columns=expected_cols)
            for col_time in ['entry_time', 'exit_time']:
                if col_time in self.executed_trades_log.columns:
                    self.executed_trades_log[col_time] = pd.to_datetime(self.executed_trades_log[col_time])

    def plot_equity_curve_and_trades(self, title: str = "Equity Curve with Trades") -> None:
        """Displays the equity curve chart."""
        df_plot = self.executed_trades_log
        if 'equity_after_trade' not in df_plot.columns or 'exit_time' not in df_plot.columns or df_plot.empty:
            print(
                "Cannot plot equity curve: "
                "missing 'equity_after_trade' or 'exit_time' columns, or no executed trades."
            )
            return

        plt.figure(figsize=(12, 6))
        plt.plot(df_plot['exit_time'], df_plot['equity_after_trade'], label="Equidad")

        winning_trades = df_plot[df_plot['profit'] > 0]
        losing_trades = df_plot[df_plot['profit'] <= 0]

        plt.scatter(
            winning_trades['exit_time'].dropna(),
            winning_trades['equity_after_trade'].dropna(),  # dropna para evitar errores con NaT
            color='green',
            marker='^',
            label='Winning Trades',
            s=50,
            zorder=2
        )
        plt.scatter(
            losing_trades['exit_time'].dropna(),
            losing_trades['equity_after_trade'].dropna(),  # dropna para evitar errores con NaT
            color='red',
            marker='v',
            label='Losing/Neutral Trades',
            s=50,
            zorder=2
        )

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
        if "Winning Trades" not in metrics or "Losing/Neutral Trades" not in metrics:
            print(
                "Cannot plot trade count: "
                "missing 'Winning Trades' or 'Losing/Neutral Trades' metrics."
            )
            return

        labels = ['Winning', 'Losing/Neutral']
        counts = [metrics["Winning Trades"], metrics["Losing/Neutral Trades"]]

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
        df_plot = self.executed_trades_log
        if 'drawdown_dollars' not in df_plot.columns or 'exit_time' not in df_plot.columns or df_plot.empty:
            print(
                "Cannot plot drawdown curve: "
                "missing 'drawdown_dollars' or 'exit_time' columns, or no executed trades."
            )
            return
        plt.figure(figsize=(12, 6))
        plt.plot(
            df_plot['exit_time'].dropna(),  # dropna para evitar errores con NaT
            df_plot['drawdown_dollars'].dropna(),
            label="Drawdown ($)",
            color='red'
        )
        plt.fill_between(
            df_plot['exit_time'].dropna(),  # dropna para evitar errores con NaT
            df_plot['drawdown_dollars'].dropna(),
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
        metrics: Dict[str, Any] = {}
        # Usar self.trade_log para métricas generales (incluyendo canceladas)
        df_all_attempts = self.trade_log
        # Usar self.executed_trades_log para métricas de rendimiento de trades ejecutados
        df_executed = self.executed_trades_log

        metrics["Total Intentos Registrados"] = len(df_all_attempts)
        if metrics["Total Intentos Registrados"] == 0:
            # Si no hay intentos registrados, no se pueden calcular otras métricas.
            # Actualizar el mensaje para ser más genérico.
            metrics["Message"] = "No se registraron intentos de operación."
            return {}

        # Nueva métrica: Operaciones canceladas por el sentiment analyzer
        if "cancellation_reason" in df_all_attempts.columns:
            cancelled_by_sentiment = df_all_attempts[
                df_all_attempts["cancellation_reason"] == "SENTIMENT_ANALYZER"
            ]
            metrics["Operaciones Canceladas por Sentiment Analyzer"] = (
                len(cancelled_by_sentiment)
            )
        else:
            metrics["Operaciones Canceladas por Sentiment Analyzer"] = (
                "N/A (columna 'cancellation_reason' no disponible)"
            )

        # Métricas basadas en trades ejecutados
        metrics["Total Operaciones Ejecutadas"] = len(df_executed)

        if metrics["Total Operaciones Ejecutadas"] > 0:
            if 'profit' not in df_executed.columns:
                print(
                    "Advertencia: 'profit' column is missing in executed_trades_log for performance metrics."
                )
                # Inicializar métricas de rendimiento a N/A o 0 si 'profit' no está
                metrics.update({
                    "Total Profit/Loss": "N/A", "Gross Profit": "N/A", "Gross Loss": "N/A",
                    "Winning Trades": "N/A", "Losing/Neutral Trades": "N/A", "Win Rate (%)": "N/A",
                    "Average Win ($)": "N/A", "Average Loss ($)": "N/A", "Profit Factor": "N/A",
                    "Max Drawdown ($)": "N/A", "Max Drawdown (%)": "N/A", "Sharpe Ratio (simplificado)": "N/A"
                })
                return metrics  # Retornar si no hay 'profit' en trades ejecutados

            metrics["Total Profit/Loss"] = df_executed['profit'].sum()
            metrics["Gross Profit"] = df_executed[df_executed['profit'] > 0]['profit'].sum()
            metrics["Gross Loss"] = df_executed[df_executed['profit'] < 0]['profit'].sum()

            winning_trades_df = df_executed[df_executed['profit'] > 0]
            losing_neutral_trades_df = df_executed[df_executed['profit'] <= 0]
            actual_losing_trades_df = df_executed[df_executed['profit'] < 0]

            metrics["Winning Trades"] = len(winning_trades_df)
            metrics["Losing/Neutral Trades"] = len(losing_neutral_trades_df)  # Usar la cuenta correcta

            metrics["Win Rate (%)"] = (
                (metrics["Winning Trades"] / metrics["Total Operaciones Ejecutadas"]) * 100
                if metrics["Total Operaciones Ejecutadas"] > 0 else 0
            )

            metrics["Average Win ($)"] = (
                winning_trades_df['profit'].mean()
                if not winning_trades_df.empty else 0
            )
            metrics["Average Loss ($)"] = (
                actual_losing_trades_df['profit'].mean()
                if not actual_losing_trades_df.empty else 0
            )

            metrics["Profit Factor"] = (
                abs(metrics["Gross Profit"] / metrics["Gross Loss"])
                if metrics["Gross Loss"] != 0 else np.inf
            )

            metrics["Max Drawdown ($)"] = (
                df_executed['drawdown_dollars'].min()
                if 'drawdown_dollars' in df_executed.columns
                and not df_executed['drawdown_dollars'].empty
                else "N/A"
            )
            metrics["Max Drawdown (%)"] = (
                abs(df_executed['drawdown_percent'].min())
                if 'drawdown_percent' in df_executed.columns
                and not df_executed['drawdown_percent'].empty
                else "N/A"
            )

            if len(df_executed['profit']) > 1:  # Necesita al menos 2 trades para std dev
                initial_balance_val = (
                    self.initial_balance
                    if isinstance(self.initial_balance, (int, float)) and self.initial_balance != 0
                    else 1.0
                )
                returns = df_executed['profit'] / initial_balance_val
                if returns.std() != 0 and not np.isnan(returns.std()):
                    sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)  # Asumiendo datos diarios
                else:
                    sharpe_ratio = 0 if returns.mean() == 0 else np.inf  # o manejar de otra forma si std es 0
                metrics["Sharpe Ratio (simplificado)"] = sharpe_ratio
            else:
                metrics["Sharpe Ratio (simplificado)"] = "N/A (datos insuficientes)"
        else:
            # No hay operaciones ejecutadas, inicializar métricas de rendimiento
            metrics.update({
                "Total Profit/Loss": 0, "Gross Profit": 0, "Gross Loss": 0,
                "Winning Trades": 0, "Losing/Neutral Trades": 0, "Win Rate (%)": 0,
                "Average Win ($)": 0, "Average Loss ($)": 0, "Profit Factor": "N/A",
                "Max Drawdown ($)": "N/A", "Max Drawdown (%)": "N/A", "Sharpe Ratio (simplificado)": "N/A"
            })

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
