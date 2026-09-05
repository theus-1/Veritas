from app.schemas.search import SearchResult
from app.services.search_service import SearchService


def test_search_returns_results(monkeypatch):

    fake_results = [
        SearchResult(
            title="Notícia de teste",
            url="https://exemplo.com/noticia",
            source_name="Fonte de teste",
            snippet="Descrição da notícia."
        )
    ]

    def fake_search(self, query):
        return fake_results

    monkeypatch.setattr(
        "app.clients.gnews_client.GNewsClient.search",
        fake_search
    )

    service = SearchService()

    results = service.search("Brasil ganhou o jogo")

    assert len(results) == 1
    assert results[0].title == "Notícia de teste"
    assert results[0].url == "https://exemplo.com/noticia"
    assert results[0].source_name == "Fonte de teste"
    assert results[0].snippet == "Descrição da notícia."


def test_search_service_loads_config():

    service = SearchService()

    assert service.config.app_name == "Veritas"
    assert service.config.gnews_base_url == "https://gnews.io/api/v4"
    assert service.config.gnews_api_key
