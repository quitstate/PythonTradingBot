from transformers import pipeline
from datetime import datetime, timedelta
import os
import pandas as pd


class BacktestSentimentAnalyzer:
    def __init__(self,
                 csv_file_path: str,
                 model_name="ProsusAI/finbert"):
        self.analyzer = pipeline("sentiment-analysis", model=model_name)
        self.csv_file_path = csv_file_path

        self.tokenizer_max_length = 512  # Longitud máxima para FinBERT
        # Cache para DataFrames de noticias cargados y filtrados del CSV: {ticker_str: pd.DataFrame}
        self.loaded_news_data_cache = {}
        # Cache para sentimiento analizado:
        # {(ticker, bar_date_str, lookback_days, articles_to_analyze): sentiment_info}
        self.sentiment_cache = {}

        self.master_news_df = pd.DataFrame()  # Inicializar como DataFrame vacío
        self._preload_csv_data()  # Cargar el CSV al inicio

    def _preload_csv_data(self):
        """
        Carga el archivo CSV completo en memoria y lo preprocesa.
        Este método se llama una vez durante la inicialización.
        """
        if not self.csv_file_path or not os.path.exists(self.csv_file_path):
            print(f"ERROR: CSV file path not provided or file not found: {self.csv_file_path}. "
                  "Sentiment analysis from CSV will not be available.")
            return  # self.master_news_df permanece vacío

        try:
            print(f"INFO: Loading news data from CSV: {self.csv_file_path}")
            self.master_news_df = pd.read_csv(self.csv_file_path)

            # Validaciones de columnas esenciales
            required_cols = ['published_at', 'ticker', 'text']
            missing_cols = [col for col in required_cols if col not in self.master_news_df.columns]
            if missing_cols:
                raise ValueError(f"CSV must contain the following columns: {', '.join(missing_cols)}.")

            if 'title' not in self.master_news_df.columns:
                print(
                    "WARN: 'title' column not found in CSV. "
                    "Will use 'text' only for sentiment if title is missing for a row."
                )
                self.master_news_df['title'] = ""  # Añadir columna vacía si no existe para evitar KeyErrors

            self.master_news_df['published_at'] = pd.to_datetime(
                self.master_news_df['published_at'], errors='coerce'
            )

            # Eliminar filas donde las columnas cruciales (después de la conversión de fecha) son NaN
            self.master_news_df.dropna(subset=['published_at', 'ticker', 'text'], inplace=True)

            # Asegurar que 'title' y 'text' sean strings, rellenando NaN con string vacío
            self.master_news_df['title'] = self.master_news_df['title'].fillna('').astype(str)
            self.master_news_df['text'] = self.master_news_df['text'].fillna('').astype(str)

            self.master_news_df.sort_values(by='published_at', inplace=True)
            print(
                "INFO: Successfully loaded and preprocessed "
                f"{len(self.master_news_df)} news items from CSV."
            )
        except FileNotFoundError:
            print(
                f"ERROR: CSV file not found at {self.csv_file_path}. "
                "Sentiment analysis from CSV will fail."
            )
        except ValueError as ve:
            print(f"ERROR: ValueError while processing CSV {self.csv_file_path}: {ve}")
        except Exception as e:
            print(f"ERROR: An unexpected error occurred while loading CSV {self.csv_file_path}: {e}")
            self.master_news_df = pd.DataFrame()  # Asegurar que sea un DF vacío en caso de error grave

    def _get_news_for_ticker_from_csv(self, ticker: str) -> pd.DataFrame | None:
        """
        Filtra el DataFrame maestro para un ticker específico y lo cachea.
        """
        if self.master_news_df.empty:
            # El error ya se mostró en _preload_csv_data si el archivo no se cargó
            return None

        ticker_upper = ticker.upper()
        if ticker_upper in self.loaded_news_data_cache:
            return self.loaded_news_data_cache[ticker_upper]

        ticker_df = self.master_news_df[
            self.master_news_df['ticker'].fillna('').str.upper() == ticker_upper
        ].copy()

        if ticker_df.empty:
            print(f"WARN: No news found for ticker '{ticker}' in the loaded CSV data.")
            self.loaded_news_data_cache[ticker_upper] = pd.DataFrame()
            return pd.DataFrame()

        self.loaded_news_data_cache[ticker_upper] = ticker_df
        print(f"INFO: Filtered and cached {len(ticker_df)} news items for ticker '{ticker}'.")
        return ticker_df

    def get_sentiment_for_bar_date(
        self, query_ticker: str, bar_date: datetime, lookback_days: int = 1, articles_to_analyze: int = 10
    ) -> dict:
        print(
            f"INFO: Analyzing sentiment for ticker '{query_ticker}' on date '{bar_date}' "
            f"with lookback of {lookback_days} days and analyzing {articles_to_analyze} articles."
        )
        bar_date_str = bar_date.strftime("%Y-%m-%d")

        cache_key = (query_ticker, bar_date_str, lookback_days, articles_to_analyze)
        if cache_key in self.sentiment_cache:
            return self.sentiment_cache[cache_key]

        news_df_for_ticker = self._get_news_for_ticker_from_csv(query_ticker)

        if news_df_for_ticker is None or news_df_for_ticker.empty:
            result = {
                "positive_count": 0, "negative_count": 0, "neutral_count": 0,
                "total_analyzed": 0, "average_sentiment_score": 0.0,
                "error": f"No news data available in CSV for ticker '{query_ticker}'."
            }
            self.sentiment_cache[cache_key] = result
            return result

        bar_date_naive = bar_date.replace(tzinfo=None)
        to_date_filter = bar_date_naive
        from_date_filter = bar_date_naive - timedelta(days=lookback_days)

        # Asumimos que 'published_at' ya es datetime y tz-naive desde _preload_csv_data
        relevant_news_df = news_df_for_ticker[
            (news_df_for_ticker['published_at'] >= from_date_filter) &
            (news_df_for_ticker['published_at'] <= to_date_filter)
        ]

        news_items_to_process = []
        if not relevant_news_df.empty:
            # Tomar los 'articles_to_analyze' más recientes del periodo filtrado
            for _, row in relevant_news_df.nlargest(articles_to_analyze, 'published_at').iterrows():
                title = row.get('title', '')  # Ya es string por el preprocesamiento
                text_content = row.get('text', '')  # Ya es string

                full_text = title
                if text_content:
                    if full_text and not full_text.endswith('.'):
                        full_text += ". "
                    full_text += text_content

                # Asegurar que no procesamos strings vacíos o que solo contienen un punto
                if full_text.strip() and full_text.strip() != ".":
                    news_items_to_process.append(full_text.strip())

        if not news_items_to_process:
            result = {
                "positive_count": 0, "negative_count": 0, "neutral_count": 0,
                "total_analyzed": 0, "average_sentiment_score": 0.0,
                "error": f"No news found for ticker '{query_ticker}' in CSV for date range "
                         f"{from_date_filter.strftime('%Y-%m-%d')} to {to_date_filter.strftime('%Y-%m-%d')}."
            }
            self.sentiment_cache[cache_key] = result
            return result

        positive_count = 0
        negative_count = 0
        neutral_count = 0
        weighted_score_sum = 0.0

        for news_item_text in news_items_to_process:
            try:
                # Truncar el texto si es más largo que la longitud máxima permitida por el tokenizador
                truncated_text = news_item_text[:self.tokenizer_max_length]

                analysis_result_list = self.analyzer(truncated_text)
                if analysis_result_list:
                    analysis_result = analysis_result_list[0]
                    label, score = analysis_result['label'], analysis_result['score']

                    if label.lower() == "positive":
                        positive_count += 1
                        weighted_score_sum += score
                    elif label.lower() == "negative":
                        negative_count += 1
                        weighted_score_sum -= score
                    elif label.lower() == "neutral":
                        neutral_count += 1
                else:
                    print(f"WARN (Sentiment): Analyzer returned empty result for: '{truncated_text[:50]}...'")
            except Exception as e:
                print(f"Error (Sentiment) analyzing news item '{truncated_text[:50]}...': {e}")

        total_analyzed = positive_count + negative_count + neutral_count
        average_sentiment_score = (weighted_score_sum / total_analyzed) if total_analyzed > 0 else 0.0

        result = {
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "total_analyzed": total_analyzed,
            "average_sentiment_score": round(average_sentiment_score, 4)
        }
        self.sentiment_cache[cache_key] = result
        return result
