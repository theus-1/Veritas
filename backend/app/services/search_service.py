import re

from app.clients.gnews_client import GNewsClient
from app.core.config import Config


class SearchService:

    STOPWORDS = {
        "a",
        "à",
        "às",
        "ao",
        "aos",
        "as",
        "com",
        "como",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "e",
        "em",
        "entre",
        "foi",
        "foram",
        "na",
        "nas",
        "no",
        "nos",
        "o",
        "os",
        "ou",
        "para",
        "por",
        "que",
        "se",
        "sem",
        "sobre",
        "um",
        "uma",
        "uns",
        "umas",
    }

    GENERIC_WORDS = {
        "anunciou",
        "anuncia",
        "anunciar",
        "aumentou",
        "aumento",
        "caiu",
        "queda",
        "cresceu",
        "crescimento",
        "crescer",
        "ficou",
        "resultado",
        "mesmo",
        "novas",
        "novo",
        "novos",
        "nova",
        "passado",
        "relação",
        "comparação",
        "período",
        "ano",
        "anterior",
        "avançou",
        "acima",
        "expectativas",
        "economistas",
        "projetavam",
        "trimestral",
        "aproximadamente",
    }

    TERM_REPLACEMENTS = {
        "Produto Interno Bruto": "PIB",
        "produto interno bruto": "PIB",
    }

    PERIOD_EXPRESSIONS = {
        "primeiro trimestre",
        "segundo trimestre",
        "terceiro trimestre",
        "quarto trimestre",
        "primeiro semestre",
        "segundo semestre",
    }

    MAX_QUERY_LENGTH = 100
    MIN_RESULTS = 3
    MAX_SEARCHES_PER_CLAIM = 3

    def __init__(self):
        self.config = Config()
        self.client = GNewsClient(self.config)

    def search(self, query: str):
        queries = self._build_queries(query)

        all_results = []

        for search_query in queries[:self.MAX_SEARCHES_PER_CLAIM]:
            if not search_query:
                continue

            results = self.client.search(search_query)

            all_results.extend(results)

            if len(self._deduplicate_results(all_results)) >= self.MIN_RESULTS:
                break

        return self._deduplicate_results(all_results)

    def _build_queries(self, text: str) -> list[str]:
        normalized_text = self._normalize_text(text)

        if not normalized_text:
            return []

        concepts = self._extract_concepts(
            normalized_text
        )

        queries = [
            self._build_specific_query(concepts),
            self._build_medium_query(concepts),
            self._build_broad_query(concepts),
        ]

        queries = [
            query
            for query in queries
            if query
        ]

        return list(dict.fromkeys(queries))

    def _normalize_text(self, text: str) -> str:
        # Remove percentuais.
        text = re.sub(
            r"\d+(?:[.,]\d+)?\s*%",
            " ",
            text
        )

        # Remove números que não sejam anos.
        text = re.sub(
            r"\b(?!20\d{2}\b)\d+(?:[.,]\d+)?\b",
            " ",
            text
        )

        # Remove pontuação.
        text = re.sub(
            r"[^\w\s]",
            " ",
            text
        )

        # Substitui termos conhecidos.
        for expression, replacement in (
            self.TERM_REPLACEMENTS.items()
        ):
            text = text.replace(
                expression,
                replacement
            )

        return " ".join(text.split())

    def _extract_concepts(self, text: str) -> dict:
        """
        Extrai conceitos importantes da afirmação.

        Também identifica qual período é o principal
        e qual aparece apenas como comparação.
        """

        lower_text = text.lower()

        periods = []

        period_pattern = "|".join(
            re.escape(period)
            for period in sorted(
                self.PERIOD_EXPRESSIONS,
                key=len,
                reverse=True
            )
        )

        for match in re.finditer(
            period_pattern,
            lower_text
        ):
            periods.append(
                {
                    "text": match.group(0),
                    "position": match.start(),
                }
            )

        # Detecta expressões de comparação.
        comparison_position = None

        comparison_patterns = [
            "em relação ao",
            "em relação à",
            "comparado ao",
            "comparada à",
            "comparação com",
            "contra o",
            "contra a",
        ]

        for pattern in comparison_patterns:
            position = lower_text.find(pattern)

            if position != -1:
                comparison_position = position
                break

        primary_period = None
        comparison_period = None

        if periods:
            if comparison_position is not None:
                for period in periods:
                    if period["position"] < comparison_position:
                        primary_period = period["text"]
                        break

                for period in periods:
                    if period["position"] > comparison_position:
                        comparison_period = period["text"]
                        break

            if primary_period is None:
                primary_period = periods[0]["text"]

        words = text.split()

        meaningful_words = []

        for word in words:
            normalized_word = word.lower()

            if normalized_word in self.STOPWORDS:
                continue

            if normalized_word in self.GENERIC_WORDS:
                continue

            # Não adiciona palavras que fazem parte
            # de expressões de período.
            if any(
                normalized_word == part
                for period in self.PERIOD_EXPRESSIONS
                for part in period.split()
            ):
                continue

            meaningful_words.append(word)

        unique_words = list(
            dict.fromkeys(meaningful_words)
        )

        years = [
            word
            for word in unique_words
            if re.fullmatch(
                r"20\d{2}",
                word
            )
        ]

        subjects = [
            word
            for word in unique_words
            if word not in years
        ]

        return {
            "subjects": subjects,
            "years": years,
            "periods": periods,
            "primary_period": primary_period,
            "comparison_period": comparison_period,
        }

    def _build_specific_query(
        self,
        concepts: dict
    ) -> str:

        subjects = concepts["subjects"]
        years = concepts["years"]
        primary_period = concepts["primary_period"]

        selected = []

        selected.extend(subjects[:3])

        if primary_period:
            selected.append(primary_period)

        if years:
            selected.append(years[0])

        return self._clean_query(selected)

    def _build_medium_query(
        self,
        concepts: dict
    ) -> str:

        subjects = concepts["subjects"]
        years = concepts["years"]

        selected = []

        selected.extend(subjects[:4])

        if years:
            selected.append(years[0])

        return self._clean_query(selected)

    def _build_broad_query(
        self,
        concepts: dict
    ) -> str:

        subjects = concepts["subjects"]
        years = concepts["years"]

        selected = []

        selected.extend(subjects[:2])

        if years:
            selected.append(years[0])

        return self._clean_query(selected)

    def _clean_query(
        self,
        words: list[str]
    ) -> str:

        cleaned = []

        for word in words:
            if not word:
                continue

            if word.lower() in self.STOPWORDS:
                continue

            if word not in cleaned:
                cleaned.append(word)

        query = " ".join(cleaned)

        query = " ".join(query.split())

        query = query[:self.MAX_QUERY_LENGTH]

        return query.strip()

    def _build_query(self, text: str) -> str:
        queries = self._build_queries(text)

        if not queries:
            return ""

        return queries[0]

    def _deduplicate_results(self, results):
        unique_results = []
        seen_urls = set()

        for result in results:
            if result.url in seen_urls:
                continue

            seen_urls.add(result.url)
            unique_results.append(result)

        return unique_results
