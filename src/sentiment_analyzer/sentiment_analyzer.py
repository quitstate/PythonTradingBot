import requests
from transformers import pipeline
from datetime import datetime, timedelta
# import os


class SentimentAnalyzer:
    def __init__(self, api_key: str, model_name="ProsusAI/finbert"):
        # Ejemplo usando FinBERT, que es más específico para finanzas.
        # Otros modelos generales: "distilbert-base-uncased-finetuned-sst-2-english"
        # Es importante notar que FinBERT puede tener etiquetas diferentes (positive, negative, neutral)
        # y podrías necesitar ajustar cómo interpretas los resultados.
        self.analyzer = pipeline("sentiment-analysis", model=model_name)
        self.api_key = api_key
        if not self.api_key:
            print("WARN: SentimentAnalyzer initialized without a News API key. News fetching will fail.")

    def analyze(self, text):
        result = self.analyzer(text)[0]
        # FinBERT podría devolver 'positive', 'negative', 'neutral'.
        # El modelo SST-2 devuelve 'POSITIVE', 'NEGATIVE'.
        # Asegúrate de que la lógica que consume esto maneje las etiquetas correctamente.
        return result['label'], result['score']

    def get_news(
        self,
        query: str,
        language: str = "en",
        page_size: int = 10,
        from_date: str | None = None,
        to_date: str | None = None
    ) -> list[str]:
        """
        Fetches news articles for a given query (e.g., stock symbol or currency pair).
        :param query: The search query.
        :param language: The language of the news.
        :param page_size: The number of articles to return.
        :param from_date: Optional. The oldest date to fetch news from (YYYY-MM-DD).
        :param to_date: Optional. The newest date to fetch news up to (YYYY-MM-DD).
        """
        if not self.api_key:
            print("ERROR: No API key provided to SentimentAnalyzer for fetching news.")
            return []
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": language,
            "pageSize": page_size,
            "sortBy": "publishedAt",
            "apiKey": self.api_key,
        }
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            # Log para depuración de la respuesta de NewsAPI
            print(
                f"DEBUG: NewsAPI request for query='{query}', from_date='{from_date}', to_date='{to_date}'. "
                f"Status: {response.status_code}, TotalResults: {response.json().get('totalResults')}"
                # response.json() puede ser muy verboso, opcionalmente loguear solo si hay error o menos info
            )
            data = response.json()
            if data.get("status") == "ok":
                return [
                    article["title"] + ". " + (article.get("description", "") or "")
                    for article in data.get("articles", [])
                    if article.get("title")
                ]
            else:
                print(
                    f"ERROR: NewsAPI request failed with status {data.get('status')}: "
                    f"{data.get('message')}"
                )
                return []
        except requests.exceptions.RequestException as e:
            print(f"ERROR fetching news (RequestException): {e}")
            return []
        except Exception as e:
            print(f"ERROR processing news response: {e}")
            return []

    def analyze_sentiment_last_week(self, query: str, page_size: int = 10) -> dict:
        """
        Fetches up to 'page_size' news articles from the last week for a given query,
        analyzes their sentiment, and returns an aggregated result.
        """
        two_week_ago = datetime.now() - timedelta(days=14)
        from_date_str = two_week_ago.strftime("%Y-%m-%d")
        current_date_str = datetime.now().strftime("%Y-%m-%d")

        news_items = self.get_news(
            query=query,
            page_size=page_size,
            from_date=from_date_str,
            to_date=current_date_str
        )

        if news_items:
            print(
                f"DEBUG: Fetched {len(news_items)} news items for '{query}'. "
                f"First item: '{news_items[0][:100]}...'"
            )
        else:
            print(f"DEBUG: No news items fetched for '{query}' from last week.")

        if not news_items:
            return {
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "total_analyzed": 0,
                "average_sentiment_score": 0.0,
                "error": "No news items found or error fetching news."
            }

        positive_count = 0
        negative_count = 0
        neutral_count = 0  # Inicializar contador para neutrales
        weighted_score_sum = 0.0

        for news_item_text in news_items:
            if not news_item_text.strip():
                continue
            try:
                label, score = self.analyze(news_item_text)
                print(
                    f"DEBUG: Analyzed news item: '{news_item_text[:50]}...' "
                    f"-> Label: {label}, Score: {score:.4f}"
                )
                # FinBERT usa etiquetas en minúscula: 'positive', 'negative', 'neutral'
                if label == "positive":
                    positive_count += 1
                    weighted_score_sum += score
                elif label == "negative":
                    negative_count += 1
                    weighted_score_sum -= score
                elif label == "neutral":
                    neutral_count += 1
                    # Las noticias neutrales no suman ni restan al weighted_score_sum
                    # para el sesgo direccional
            except Exception as e:
                print(f"Error analyzing sentiment for a news item: {e}")

        total_analyzed = positive_count + negative_count + neutral_count  # Incluir neutrales en el total
        average_sentiment_score = (weighted_score_sum / total_analyzed) if total_analyzed > 0 else 0.0

        return {
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "total_analyzed": total_analyzed,
            "average_sentiment_score": round(average_sentiment_score, 4)
        }


# # --- Example Usage ---
# if __name__ == "__main__":
#     from dotenv import load_dotenv, find_dotenv

#     load_dotenv(find_dotenv())
#     NEWS_API_KEY = os.getenv("NEWS_API_KEY")

#     if not NEWS_API_KEY:
#         print("ERROR: NEWS_API_KEY not found in environment variables. Please set it in your .env file.")
#     else:
#         sa = SentimentAnalyzer(api_key=NEWS_API_KEY)

#         # --- Test individual news analysis (original example) ---
#         print("\n--- Individual News Analysis (Example) ---")
#         example_news_list = sa.get_news(query="EURUSD", page_size=2)  # Fetch 2 for brevity
#         if not example_news_list:
#             print("No news obtained for individual analysis example.")
#         for idx, noticia in enumerate(example_news_list, 1):
#             label, score = sa.analyze(noticia)
#             print(f"Noticia {idx}: {noticia[:100]}...")  # Print first 100 chars
#             print(f"  Sentimiento: {label}, Confianza: {score:.2f}\n")

#         # --- Test aggregated sentiment for last week ---
#         print("\n--- Aggregated Sentiment Analysis for 'USD' (Last Week) ---")
#         # Using a more general query like "USD" or "EUR" might yield more news
#         # than a specific pair like "EURUSD" for a whole week.
#         aggregated_sentiment_usd = sa.analyze_sentiment_last_week(query="USD", page_size=10)
#         print("Aggregated Sentiment for 'USD':")
#         for key, value in aggregated_sentiment_usd.items():
#             print(f"  {key}: {value}")

#         print("\n--- Aggregated Sentiment Analysis for 'EURUSD' (Last Week) ---")
#         aggregated_sentiment_eurusd = sa.analyze_sentiment_last_week(query="EURUSD", page_size=10)
#         print("Aggregated Sentiment for 'EURUSD':")
#         for key, value in aggregated_sentiment_eurusd.items():
#             print(f"  {key}: {value}")
