import httpx

from app.core.config import Config
from app.schemas.search import SearchResult


class GNewsClient:

    def __init__(self, config: Config):
        self.config = config

    def search(self, query: str):
        if not self.config.gnews_enabled:
            return []

        url = f"{self.config.gnews_base_url}/search"

        api_keys = [
            self.config.gnews_api_key,
            self.config.gnews_api_key2
        ]

        for index, api_key in enumerate(api_keys):
            params = {
                "q": query,
                "apikey": api_key
            }

            response = httpx.get(url, params=params)

            if response.status_code == 403:
                if index == 0:
                    continue

                raise RuntimeError(
                    "As duas chaves da GNews estão sem cota disponível."
                )

            response.raise_for_status()

            data = response.json()
            articles = data.get("articles", [])

            results = []

            for article in articles:
                result = SearchResult(
                    title=article["title"],
                    url=article["url"],
                    source_name=article["source"]["name"],
                    snippet=article["description"]
                )

                results.append(result)

            return results

        raise RuntimeError(
            "As duas chaves da GNews estão sem cota disponível."
        )
