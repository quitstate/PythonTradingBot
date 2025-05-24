import requests
from transformers import pipeline
import os
from dotenv import load_dotenv, find_dotenv
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)


class SentimentAnalyzer:
    def __init__(self, model_name="distilbert-base-uncased-finetuned-sst-2-english"):
        self.analyzer = pipeline("sentiment-analysis", model=model_name)

    def analyze(self, text):
        result = self.analyzer(text)[0]
        return result['label'], result['score']


def get_eurusd_news(api_key, query="EURUSD", language="en", page_size=5):
    if not api_key:
        print("ERROR: No API key provided.")
        return []
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": language,
        "pageSize": page_size,
        "sortBy": "publishedAt",
        "apiKey": api_key
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "ok":
            print("ERROR: NewsAPI returned an error:", data.get("message"))
            return []
        return [
            article["title"] + ". " + article.get("description", "")
            for article in data.get("articles", [])
        ]
    except Exception as e:
        print("ERROR fetching news:", e)
        return []


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv(find_dotenv())
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    print("API KEY:", NEWS_API_KEY)
    # NEWS_API_KEY = "tu_api_key_aqui"  # Descomenta para pruebas rápidas
    sa = SentimentAnalyzer()
    noticias = get_eurusd_news(NEWS_API_KEY)
    if not noticias:
        print("No se pudieron obtener noticias. Verifica tu API key y conexión.")
    for idx, noticia in enumerate(noticias, 1):
        label, score = sa.analyze(noticia)
        print(f"Noticia {idx}: {noticia}")
        print(f"  Sentimiento: {label}, Confianza: {score:.2f}\n")
