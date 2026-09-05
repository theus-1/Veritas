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
    assert service.config.parsed_gnews_api_keys


def test_build_query_returns_specific_query():
    service = SearchService()

    query = service._build_query(
        "O Produto Interno Bruto do Brasil cresceu "
        "0,5% no segundo trimestre de 2026 "
        "em relação ao primeiro trimestre"
    )

    assert query == "PIB Brasil segundo trimestre 2026"


def test_build_query_removes_percentages():
    service = SearchService()

    query = service._build_query(
        "O PIB do Brasil cresceu 0,5% "
        "no segundo trimestre de 2026"
    )

    query_words = query.split()

    assert "0" not in query_words
    assert "5" not in query_words
    assert "%" not in query


def test_build_query_preserves_year():
    service = SearchService()

    query = service._build_query(
        "O PIB do Brasil cresceu em 2026"
    )

    assert "2026" in query


def test_build_query_preserves_period():
    service = SearchService()

    query = service._build_query(
        "O PIB cresceu no segundo trimestre de 2026"
    )

    assert "segundo trimestre" in query


def test_build_queries_generates_fallbacks():
    service = SearchService()

    queries = service._build_queries(
        "O Produto Interno Bruto do Brasil cresceu "
        "0,5% no segundo trimestre de 2026 "
        "em relação ao primeiro trimestre"
    )

    assert len(queries) >= 2
    assert queries[0] == "PIB Brasil segundo trimestre 2026"


def test_build_queries_does_not_repeat_queries():
    service = SearchService()

    queries = service._build_queries(
        "PIB Brasil 2026"
    )

    assert len(queries) == len(set(queries))


def test_search_uses_fallback_when_first_query_is_empty(
    monkeypatch
):
    captured_queries = []

    def fake_search(self, query):
        captured_queries.append(query)

        if len(captured_queries) == 1:
            return []

        return [
            SearchResult(
                title="Resultado encontrado",
                url="https://exemplo.com/resultado",
                source_name="Fonte",
                snippet="Descrição."
            )
        ]

    monkeypatch.setattr(
        "app.clients.gnews_client.GNewsClient.search",
        fake_search
    )

    service = SearchService()

    results = service.search(
        "O Produto Interno Bruto do Brasil cresceu "
        "0,5% no segundo trimestre de 2026 "
        "em relação ao primeiro trimestre"
    )

    assert len(results) == 1
    assert len(captured_queries) >= 2


def test_search_stops_when_enough_results_are_found(
    monkeypatch
):
    captured_queries = []

    def fake_search(self, query):
        captured_queries.append(query)

        return [
            SearchResult(
                title=f"Resultado {index}",
                url=f"https://exemplo.com/{index}",
                source_name="Fonte",
                snippet="Descrição."
            )
            for index in range(3)
        ]

    monkeypatch.setattr(
        "app.clients.gnews_client.GNewsClient.search",
        fake_search
    )

    service = SearchService()

    results = service.search(
        "Produto Interno Bruto Brasil 2026"
    )

    assert len(results) == 3
    assert len(captured_queries) == 1


def test_search_deduplicates_results(monkeypatch):
    def fake_search(self, query):
        return [
            SearchResult(
                title="Resultado 1",
                url="https://exemplo.com/mesma",
                source_name="Fonte",
                snippet="Descrição."
            ),
            SearchResult(
                title="Resultado 2",
                url="https://exemplo.com/mesma",
                source_name="Fonte",
                snippet="Outra descrição."
            ),
            SearchResult(
                title="Resultado 3",
                url="https://exemplo.com/outra",
                source_name="Fonte",
                snippet="Descrição."
            ),
        ]

    monkeypatch.setattr(
        "app.clients.gnews_client.GNewsClient.search",
        fake_search
    )

    service = SearchService()

    results = service.search(
        "Produto Interno Bruto Brasil 2026"
    )

    assert len(results) == 2


def test_search_uses_optimized_query(monkeypatch):
    captured_queries = []

    def fake_search(self, query):
        captured_queries.append(query)

        return [
            SearchResult(
                title=f"Resultado {index}",
                url=f"https://exemplo.com/{index}",
                source_name="Fonte",
                snippet="Descrição."
            )
            for index in range(3)
        ]

    monkeypatch.setattr(
        "app.clients.gnews_client.GNewsClient.search",
        fake_search
    )

    service = SearchService()

    service.search(
        "O Produto Interno Bruto do Brasil cresceu "
        "0,5% no segundo trimestre de 2026"
    )

    assert captured_queries[0] == (
        "PIB Brasil segundo trimestre 2026"
    )

    assert len(captured_queries) == 1
