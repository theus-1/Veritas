import logging

from sqlalchemy.orm import Session

from app.clients.gemini_client import GeminiClient
from app.clients.groq_client import GroqClient
from app.core.config import Config
from app.core.exceptions import ExternalServiceException
from app.models.analysis import StatusEnum, VerdictEnum
from app.models.evidence import EvidenceVerdictEnum
from app.repositories.analysis_repository import AnalysisRepository
from app.schemas.analysis import AnalysisCreate
from app.services.claim_service import ClaimService
from app.services.evidence_service import EvidenceService
from app.services.search_service import SearchService


logger = logging.getLogger(__name__)


class AnalysisService:
    GEMINI_CLAIMS_PER_BATCH = 3

    GROQ_LOCAL_FALLBACK_CODES = {
    "GROQ_RATE_LIMIT",
    "GROQ_UNAVAILABLE",
    "GROQ_TIMEOUT",
    "GROQ_CONNECTION_ERROR",
    "GROQ_CONFIG_ERROR",
    "GROQ_INVALID_RESPONSE",
    }

    GEMINI_FALLBACK_CODES = {
        "GEMINI_RATE_LIMIT",
        "GEMINI_UNAVAILABLE",
        "GEMINI_TIMEOUT",
        "GEMINI_CONNECTION_ERROR",
    }

    def __init__(self):
        self.repository = AnalysisRepository()
        self.claim_service = ClaimService()
        self.search_service = SearchService()
        self.evidence_service = EvidenceService()

        self.config = Config()

        self.gemini_client = GeminiClient(
            self.config
        )

        self.groq_client = GroqClient(
            self.config
        )

    def create_analysis(
        self,
        db: Session,
        data: AnalysisCreate,
    ):
        analysis = self.repository.create(
            db=db,
            data=data,
        )

        analysis.status = StatusEnum.PROCESSING

        db.commit()
        db.refresh(analysis)

        try:
            # =========================================
            # Extração e persistência das claims
            # =========================================

            claims_text = (
                self.claim_service.extract_claims(
                    data.input_text
                )
            )

            claims = (
                self.claim_service.create_claims(
                    db,
                    analysis,
                    claims_text,
                )
            )


            prepared_claims = []

            search_texts = (
                self.claim_service
                .build_search_texts(
                    [
                        claim.text
                        for claim in claims
                    ]
                )
            )

            for claim_index, claim in enumerate(
                claims
            ):
                search_text = (
                    search_texts[
                        claim_index
                    ]
                )

                if (
                    search_text
                    != claim.text
                ):
                    logger.info(
                        "Contexto de busca enriquecido "
                        "claim_index=%s",
                        claim_index,
                    )

                results = (
                    self.search_service.search(
                        search_text
                    )
                )

                results = (
                    self.evidence_service
                    .prepare_results(
                        claim.text,
                        results,
                    )
                )

                prepared_claims.append(
                    {
                        "claim_index": claim_index,
                        "claim": claim,
                        "results": results,
                    }
                )


            assessments_by_claim = {}

            ai_batches = [
                {
                    "claim_index": (
                        item["claim_index"]
                    ),
                    "claim": (
                        item["claim"].text
                    ),
                    "results": (
                        item["results"]
                    ),
                }
                for item in prepared_claims
                if item["results"]
            ]

            for start in range(
                0,
                len(ai_batches),
                self.GEMINI_CLAIMS_PER_BATCH,
            ):
                batch = ai_batches[
                    start:
                    start
                    + self.GEMINI_CLAIMS_PER_BATCH
                ]

                logger.info(
                    "Processando IA micro-batch "
                    "%s-%s de %s claims",
                    start + 1,
                    start + len(batch),
                    len(ai_batches),
                )

                batch_assessments = (
                    self._assess_batch_with_fallback(
                        batch
                    )
                )

                assessments_by_claim.update(
                    batch_assessments
                )

            # =========================================
            # Persistência das evidências
            # + resultado individual das claims
            # =========================================

            all_evidences = []

            for item in prepared_claims:
                claim_index = (
                    item["claim_index"]
                )

                claim = item["claim"]
                results = item["results"]

                assessments = (
                assessments_by_claim.get(
                    claim_index
                )
                )

                evidences = (
                    self.evidence_service
                    .create_evidences(
                        db=db,
                        analysis=analysis,
                        claim=claim,
                        results=results,
                        assessments=assessments,
                    )
                )

                # -------------------------------------
                # Resultado individual da claim
                # -------------------------------------

                claim.confidence = (
                    self.calculate_confidence(
                        evidences
                    )
                )

                claim.verdict = (
                    self.generate_verdict(
                        evidences
                    )
                )

                all_evidences.extend(
                    evidences
                )

            # =========================================
            # Resultado geral da análise
            # =========================================

            confidence = (
                self.calculate_overall_confidence(
                    claims
                )
            )

            verdict = (
                self.generate_overall_verdict(
                    claims
                )
            )

            analysis.confidence = confidence
            analysis.verdict = verdict

            analysis.status = (
                StatusEnum.COMPLETED
            )

            db.commit()
            db.refresh(analysis)

            return analysis

        except Exception:
            db.rollback()

            try:
                analysis.status = StatusEnum.FAILED

                db.add(analysis)
                db.commit()
                db.refresh(analysis)

            except Exception:
                db.rollback()

            raise
    def _assess_batch_with_fallback(
            self,
            batch,
        ):
            # =========================================
            # 1. Provider primário: Gemini
            # =========================================

            if self.config.gemini_enabled:
                try:
                    return (
                        self.gemini_client
                        .assess_batch(
                            batch
                        )
                    )

                except ExternalServiceException as exc:
                    if (
                        exc.code
                        not in self.GEMINI_FALLBACK_CODES
                    ):
                        raise

                    logger.warning(
                        "Gemini falhou com %s. "
                        "Tentando fallback Groq.",
                        exc.code,
                    )

            groq_api_key = (
                getattr(
                    self.config,
                    "groq_api_key",
                    "",
                )
                or ""
            ).strip()

            if not groq_api_key:
                logger.warning(
                    "Groq não configurada. "
                    "Usando heurística local."
                )

                return {}

            try:
                result = (
                    self.groq_client
                    .assess_batch(
                        batch
                    )
                )

                logger.info(
                    "Fallback Groq concluído "
                    "com sucesso claims=%s",
                    len(batch),
                )

                return result

            except ExternalServiceException as exc:
                if (
                    exc.code
                    not in self.GROQ_LOCAL_FALLBACK_CODES
                ):
                    raise

                logger.warning(
                    "Groq fallback falhou "
                    "com %s. "
                    "Usando heurística local.",
                    exc.code,
                )

                return {}

    def _evidence_summary(
        self,
        evidences,
    ):
        # Uma fonte possui no máximo um voto
        # por claim e direção.
        #
        # Artigos repetidos não aumentam
        # artificialmente a confiança.

        unique = {}

        for evidence in evidences:
            direction = (
                self._get_evidence_verdict(
                    evidence
                )
            )

            if direction not in {
                EvidenceVerdictEnum.SUPPORTS,
                EvidenceVerdictEnum.CONTRADICTS,
            }:
                continue

            if (
                evidence.relevance
                < self.evidence_service.MIN_RELEVANCE
            ):
                continue

            source = (
                getattr(
                    evidence,
                    "source_name",
                    None,
                )
                or "unknown"
            ).strip().lower()

            key = (
                getattr(
                    evidence,
                    "claim_id",
                    None,
                ),
                source,
                direction,
            )

            if (
                key not in unique
                or evidence.relevance
                > unique[key].relevance
            ):
                unique[key] = evidence

        votes = list(
            unique.values()
        )

        support = sum(
            evidence.relevance
            for evidence in votes
            if self._get_evidence_verdict(
                evidence
            )
            == EvidenceVerdictEnum.SUPPORTS
        )

        against = sum(
            evidence.relevance
            for evidence in votes
            if self._get_evidence_verdict(
                evidence
            )
            == EvidenceVerdictEnum.CONTRADICTS
        )

        if not votes:
            return None

        winner = (
            EvidenceVerdictEnum.SUPPORTS
            if support >= against
            else EvidenceVerdictEnum.CONTRADICTS
        )

        winning = [
            evidence
            for evidence in votes
            if self._get_evidence_verdict(
                evidence
            )
            == winner
        ]

        sources = {
            (
                getattr(
                    evidence,
                    "source_name",
                    None,
                )
                or "unknown"
            )
            .strip()
            .lower()
            for evidence in winning
        }

        quality = (
            sum(
                evidence.relevance
                for evidence in winning
            )
            / len(winning)
        )

        consensus = (
            max(
                support,
                against,
            )
            / (
                support
                + against
            )
        )

        # Confidence representa a força
        # da conclusão vencedora,
        # independentemente da direção.

        # Diminishing returns from distinct publishers; unanimity alone is
        # insufficient for near-certainty. This is a heuristic, not a probability.
        diversity_weight = (0.76, 0.88, 0.92, 0.94, 0.95)[min(len(sources), 5) - 1]
        strength = (
            quality
            * diversity_weight
            * (
                2
                * consensus
                - 1
            )
        )

        confidence = round(
            min(
                strength,
                0.95,
            ),
            2,
        )

        return (
            winner,
            quality,
            consensus,
            len(sources),
            confidence,
        )

    def calculate_overall_confidence(
        self,
        claims,
    ) -> float | None:
        values = [
            claim.confidence
            for claim in claims
            if claim.confidence is not None
        ]

        if not values:
            return None

        return round(
            sum(values) / len(values),
            2,
        )

    def generate_overall_verdict(
        self,
        claims,
    ) -> VerdictEnum:
        directional = [
            claim
            for claim in claims
            if claim.verdict
            not in {
                None,
                VerdictEnum.INCONCLUSIVA,
            }
        ]

        if not directional:
            return VerdictEnum.INCONCLUSIVA

        scores = {
            VerdictEnum.FALSA: -2,
            VerdictEnum.PROVAVELMENTE_FALSA: -1,
            VerdictEnum.PROVAVELMENTE_VERDADEIRA: 1,
            VerdictEnum.VERDADEIRA: 2,
        }

        score = sum(
            scores.get(
                claim.verdict,
                0,
            )
            for claim in directional
        )

        average = (
            score
            / len(directional)
        )

        if average <= -1.5:
            return VerdictEnum.FALSA

        if average < 0:
            return (
                VerdictEnum
                .PROVAVELMENTE_FALSA
            )

        if average >= 1.5:
            return VerdictEnum.VERDADEIRA

        if average > 0:
            return (
                VerdictEnum
                .PROVAVELMENTE_VERDADEIRA
            )

        return VerdictEnum.INCONCLUSIVA

    def calculate_confidence(
        self,
        evidences,
    ) -> float | None:
        summary = (
            self._evidence_summary(
                evidences
            )
        )

        return (
            summary[4]
            if summary
            else None
        )

    def generate_verdict(
        self,
        evidences,
    ) -> VerdictEnum:
        summary = (
            self._evidence_summary(
                evidences
            )
        )

        if summary is None:
            return (
                VerdictEnum.INCONCLUSIVA
            )

        (
            winner,
            quality,
            consensus,
            sources,
            confidence,
        ) = summary

        if consensus < 0.75:
            return (
                VerdictEnum.INCONCLUSIVA
            )

        definitive = (
            quality >= 0.8
            and sources >= 2
            and consensus >= 0.9
            and confidence >= 0.7
        )

        if (
            winner
            == EvidenceVerdictEnum.CONTRADICTS
        ):
            if definitive:
                return VerdictEnum.FALSA

            return (
                VerdictEnum
                .PROVAVELMENTE_FALSA
            )

        if definitive:
            return VerdictEnum.VERDADEIRA

        return (
            VerdictEnum
            .PROVAVELMENTE_VERDADEIRA
        )

    def _get_evidence_verdict(
        self,
        evidence,
    ) -> EvidenceVerdictEnum | None:
        verdict = evidence.verdict

        if isinstance(
            verdict,
            EvidenceVerdictEnum,
        ):
            return verdict

        try:
            return (
                EvidenceVerdictEnum(
                    verdict
                )
            )

        except ValueError:
            return None
