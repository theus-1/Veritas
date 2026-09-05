import re
from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from app.models.analysis import Analysis, VerdictEnum
from app.models.claim import Claim


class ClaimService:
    MAX_CLAIMS_PER_ANALYSIS = 10

    ROLE_WORDS = {
        "presidente",
        "governador",
        "governadora",
        "prefeito",
        "prefeita",
        "ministro",
        "ministra",
        "senador",
        "senadora",
        "deputado",
        "deputada",
        "vereador",
        "vereadora",
        "jogador",
        "jogadora",
        "técnico",
        "tecnico",
        "treinador",
        "treinadora",
        "cantor",
        "cantora",
        "ator",
        "atriz",
        "diretor",
        "diretora",
        "CEO",
        "ceo",
    }

    # Palavras que claramente não representam
    # uma entidade depois de um cargo.
    ENTITY_BOUNDARIES = {
        "morreu",
        "morre",
        "morrer",
        "morta",
        "morto",
        "vive",
        "vivo",
        "viva",
        "está",
        "esta",
        "estava",
        "foi",
        "é",
        "e",
        "será",
        "sera",
        "viajou",
        "viaja",
        "viajar",
        "participou",
        "participa",
        "discursou",
        "disse",
        "afirmou",
        "anunciou",
        "venceu",
        "perdeu",
        "caiu",
        "cresceu",
        "aumentou",
        "diminuiu",
        "sofreu",
        "teve",
        "tem",
        "terá",
        "tera",
        "estaria",
        "está",
        "estao",
        "estão",
    }

    def extract_claims(
        self,
        text: str,
    ):
        claims = [
            frase.strip()
            for frase in re.split(
                r"(?<!\d)\.|\.(?!\d)|[!?;]+",
                text,
            )
            if frase.strip()
        ]

        return claims[
            :self.MAX_CLAIMS_PER_ANALYSIS
        ]

    def create_claims(
        self,
        db: Session,
        analysis: Analysis,
        claims: list[str],
    ):
        created_claims = []

        for claim_text in claims[
            :self.MAX_CLAIMS_PER_ANALYSIS
        ]:
            claim = Claim(
                analysis_id=analysis.id,
                text=claim_text,
            )

            db.add(claim)
            created_claims.append(claim)

        db.commit()

        return created_claims

    # =========================================
    # Contexto compartilhado para busca
    # =========================================

    def build_search_texts(
        self,
        claims: list[str],
    ) -> list[str]:
        """
        Enriquece SOMENTE o texto enviado ao
        mecanismo de busca.

        As claims originais permanecem intactas.

        Exemplo:

        Presidente Lula morreu.
        Presidente Lula morreu de overdose.
        Presidente morreu peladão.

        A terceira query poderá ser enriquecida
        para:

        Presidente lula morreu peladão

        desde que "lula" tenha sido identificado
        repetidamente como entidade associada ao
        papel "presidente".
        """

        if not claims:
            return []

        associations = (
            self._collect_role_entities(
                claims
            )
        )

        resolved = []

        for claim in claims:
            search_text = (
                self._apply_context(
                    claim,
                    associations,
                )
            )

            resolved.append(
                search_text
            )

        return resolved

    def _collect_role_entities(
        self,
        claims: list[str],
    ) -> dict[str, Counter]:
        """
        Conta entidades encontradas imediatamente
        depois de cargos/papéis.

        Exemplo:

        "Presidente Lula morreu"
                  ↓
        presidente -> lula
        """

        associations: dict[
            str,
            Counter,
        ] = defaultdict(Counter)

        for claim in claims:
            words = self._tokenize(
                claim
            )

            normalized = [
                word.lower()
                for word in words
            ]

            for index, word in enumerate(
                normalized
            ):
                if (
                    word
                    not in self.ROLE_WORDS
                ):
                    continue

                entity = (
                    self._entity_after_role(
                        words,
                        index,
                    )
                )

                if not entity:
                    continue

                associations[
                    word
                ][
                    entity.lower()
                ] += 1

        return dict(
            associations
        )

    def _entity_after_role(
        self,
        words: list[str],
        role_index: int,
    ) -> str | None:
        next_index = (
            role_index + 1
        )

        if (
            next_index
            >= len(words)
        ):
            return None

        candidate = (
            words[next_index]
        )

        normalized = (
            candidate.lower()
        )

        if (
            normalized
            in self.ROLE_WORDS
        ):
            return None

        if (
            normalized
            in self.ENTITY_BOUNDARIES
        ):
            return None

        if (
            len(normalized) < 3
        ):
            return None

        if not re.fullmatch(
            r"[A-Za-zÀ-ÖØ-öø-ÿ]+",
            candidate,
        ):
            return None

        return candidate

    def _apply_context(
        self,
        claim: str,
        associations: dict[
            str,
            Counter,
        ],
    ) -> str:
        words = self._tokenize(
            claim
        )

        if not words:
            return claim

        normalized = [
            word.lower()
            for word in words
        ]

        result = claim

        for index, role in enumerate(
            normalized
        ):
            if (
                role
                not in self.ROLE_WORDS
            ):
                continue

            candidates = (
                associations.get(
                    role
                )
            )

            if not candidates:
                continue

            # A própria claim já possui uma
            # entidade identificável depois
            # do cargo. Não sobrescrevemos.
            current_entity = (
                self._entity_after_role(
                    words,
                    index,
                )
            )

            if current_entity:
                continue

            entity = (
                self._select_context_entity(
                    candidates
                )
            )

            if not entity:
                continue

            result = (
                self._insert_entity_after_role(
                    result,
                    role,
                    entity,
                )
            )

            # Um enriquecimento por claim já
            # é suficiente e reduz o risco
            # de misturar contextos.
            break

        return result

    def _select_context_entity(
        self,
        candidates: Counter,
    ) -> str | None:
        """
        Só herda contexto quando existe uma
        entidade dominante.

        Regras:
        - deve aparecer em pelo menos 2 claims;
        - se houver concorrente, a entidade
          principal deve ter vantagem clara.
        """

        if not candidates:
            return None

        ranked = (
            candidates.most_common()
        )

        entity, count = ranked[0]

        if count < 2:
            return None

        if len(ranked) == 1:
            return entity

        second_count = (
            ranked[1][1]
        )

        # Evita situações ambíguas como:
        #
        # Presidente Lula ...
        # Presidente Lula ...
        # Presidente Bolsonaro ...
        # Presidente morreu ...
        #
        # 2 contra 1 ainda é pouco para
        # inferirmos automaticamente.
        if (
            count
            - second_count
            < 2
        ):
            return None

        return entity

    def _insert_entity_after_role(
        self,
        text: str,
        role: str,
        entity: str,
    ) -> str:
        pattern = (
            rf"\b{re.escape(role)}\b"
        )

        return re.sub(
            pattern,
            lambda match: (
                f"{match.group(0)} "
                f"{entity}"
            ),
            text,
            count=1,
            flags=re.IGNORECASE,
        )

    def _tokenize(
        self,
        text: str,
    ) -> list[str]:
        return re.findall(
            r"[A-Za-zÀ-ÖØ-öø-ÿ]+",
            text,
        )

    def calculate_confidence(
        self,
        evidences,
    ):
        if not evidences:
            return None

        relevances = [
            evidence.relevance
            for evidence
            in evidences
        ]

        total = sum(
            relevances
        )

        media = (
            total
            / len(relevances)
        )

        return media

    def generate_verdict(
        self,
        confidence: float | None,
    ):
        # Relevance alone has no factual
        # direction. The analysis service
        # classifies using
        # SUPPORTS/CONTRADICTS evidence.
        return VerdictEnum.INCONCLUSIVA
