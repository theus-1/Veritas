import logging
import re
import time

import httpx

from app.core.config import Config
from app.core.exceptions import ExternalServiceException
from app.schemas.search import SearchResult


logger = logging.getLogger(__name__)


class GNewsClient:

    REQUEST_TIMEOUT = 5.0
    REQUEST_DELAY = 1.0
    MAX_QUERY_LENGTH = 200
    MAX_RESULTS = 10

    def __init__(self, config: Config):
        self.config = config

    def _prepare_query(self, query: str) -> str:
        query = re.sub(r"[^\w\s]", " ", query)
        query = " ".join(query.split())
        query = query[:self.MAX_QUERY_LENGTH]

        return query.strip()

    def search(self, query: str):
        if not self.config.gnews_enabled:
            return []

        query = self._prepare_query(query)

        if not query:
            return []

        url = f"{self.config.gnews_base_url}/search"

        api_keys = self.config.parsed_gnews_api_keys
        if not api_keys:
            raise ExternalServiceException(
                message="O serviço de notícias não está disponível no momento.",
                code="GNEWS_CONFIG_ERROR",
            )
        quota_unavailable = False

        for index, api_key in enumerate(api_keys):
            params = {
                "q": query,
                "apikey": api_key,
                "max": self.MAX_RESULTS,
            }

            time.sleep(self.REQUEST_DELAY)

            response = self._request(
                url=url,
                params=params,
            )

            logger.info("tentativa=%s status=%s", index + 1, response.status_code)

            if response.status_code == 429:
                time.sleep(self.REQUEST_DELAY)

                response = self._request(
                    url=url,
                    params=params,
                )

                logger.info("tentativa=%s status=%s", index + 1, response.status_code)

            if response.status_code == 429:
                raise ExternalServiceException(
                    message=(
                        "A GNews atingiu o limite de requisições. "
                        "Tente novamente em alguns segundos."
                    ),
                    code="GNEWS_RATE_LIMIT",
                )


            if response.status_code == 403:
                quota_unavailable = True
                continue

            if response.status_code == 401:
                continue

            if response.status_code >= 500:
                raise ExternalServiceException(
                    message=(
                        "O serviço de notícias está "
                        "temporariamente indisponível."
                    ),
                    code="GNEWS_UNAVAILABLE",
                )

            if response.status_code >= 400:
                raise ExternalServiceException(
                    message=(
                        "A busca de notícias não pôde "
                        "ser concluída."
                    ),
                    code="GNEWS_REQUEST_ERROR",
                )

            data = self._parse_response(response)

            articles = data.get("articles")

            if not isinstance(articles, list):
                raise ExternalServiceException(
                    message=(
                        "O serviço de notícias retornou "
                        "uma resposta inválida."
                    ),
                    code="GNEWS_INVALID_RESPONSE",
                )

            results = []

            for article in articles:
                if not isinstance(article, dict):
                    continue

                source = article.get("source") or {}

                if not isinstance(source, dict):
                    continue

                title = article.get("title")
                article_url = article.get("url")
                source_name = source.get("name")

                if not all(isinstance(value, str) and value.strip() for value in (title, article_url, source_name)):
                    continue

                results.append(
                    SearchResult(
                        title=title,
                        url=article_url,
                        source_name=source_name,
                        snippet=article.get("description") if isinstance(article.get("description"), str) else "",
                    )
                )

            return results

        raise ExternalServiceException(
            message=(
                "A cota da GNews está indisponível "
                "no momento."
            ),
            code="GNEWS_QUOTA_EXCEEDED" if quota_unavailable else "GNEWS_AUTH_ERROR",
        )

    def _request(
        self,
        url: str,
        params: dict,
    ) -> httpx.Response:
        try:
            return httpx.get(
                url,
                params=params,
                timeout=self.REQUEST_TIMEOUT,
            )

        except httpx.TimeoutException:
            raise ExternalServiceException(
                message=(
                    "O serviço de notícias demorou demais "
                    "para responder."
                ),
                code="GNEWS_TIMEOUT",
            ) from None

        except httpx.RequestError:
            raise ExternalServiceException(
                message=(
                    "Não foi possível conectar ao "
                    "serviço de notícias."
                ),
                code="GNEWS_CONNECTION_ERROR",
            ) from None

    def _parse_response(
        self,
        response: httpx.Response,
    ) -> dict:
        try:
            data = response.json()

        except ValueError:
            raise ExternalServiceException(
                message=(
                    "O serviço de notícias retornou "
                    "uma resposta inválida."
                ),
                code="GNEWS_INVALID_RESPONSE",
            ) from None

        if not isinstance(data, dict):
            raise ExternalServiceException(
                message=(
                    "O serviço de notícias retornou "
                    "uma resposta inválida."
                ),
                code="GNEWS_INVALID_RESPONSE",
            )

        return data
