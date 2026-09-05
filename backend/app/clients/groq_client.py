import json
import logging
import time

import httpx

from app.clients.gemini_client import (
    Assessment,
    BatchAssessments,
    BATCH_INSTRUCTIONS,
)
from app.core.exceptions import ExternalServiceException


logger = logging.getLogger(__name__)

GROQ_BATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_index": {
                        "type": "integer",
                    },
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "evidence_index": {
                                    "type": "integer",
                                },
                                "verdict": {
                                    "type": "string",
                                    "enum": [
                                        "SUPPORTS",
                                        "CONTRADICTS",
                                        "NEUTRAL",
                                    ],
                                },
                                "relevance": {
                                    "type": "number",
                                },
                                "quote": {
                                    "type": "string",
                                },
                                "reason": {
                                    "type": "string",
                                },
                            },
                            "required": [
                                "evidence_index",
                                "verdict",
                                "relevance",
                                "quote",
                                "reason",
                            ],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": [
                    "claim_index",
                    "items",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "claims",
    ],
    "additionalProperties": False,
}


class GroqClient:
    REQUEST_TIMEOUT = 90.0
    CONNECT_TIMEOUT = 10.0

    ENDPOINT = (
        "https://api.groq.com/openai/v1/"
        "chat/completions"
    )

    def __init__(self, config):
        self.config = config

    def _api_key(self) -> str:
        return (
            getattr(
                self.config,
                "groq_api_key",
                "",
            )
            or ""
        ).strip()

    def _headers(self) -> dict:
        return {
            "Authorization": (
                f"Bearer {self._api_key()}"
            ),
            "Content-Type": "application/json",
        }

    def _request(
        self,
        payload: dict,
    ) -> httpx.Response:
        max_attempts = 2
        retry_delays = [1]

        last_response = None

        for attempt in range(
            max_attempts
        ):
            try:
                response = httpx.post(
                    self.ENDPOINT,
                    headers=self._headers(),
                    json=payload,
                    timeout=httpx.Timeout(
                        self.REQUEST_TIMEOUT,
                        connect=(
                            self.CONNECT_TIMEOUT
                        ),
                    ),
                )

                last_response = response

            except httpx.TimeoutException:
                if (
                    attempt
                    == max_attempts - 1
                ):
                    self.fail(
                        "GROQ_TIMEOUT"
                    )

                delay = (
                    retry_delays[
                        attempt
                    ]
                )

                logger.warning(
                    "Groq timeout "
                    "tentativa=%s/%s "
                    "retry_em=%ss",
                    attempt + 1,
                    max_attempts,
                    delay,
                )

                time.sleep(delay)

                continue

            except httpx.RequestError:
                self.fail(
                    "GROQ_CONNECTION_ERROR"
                )

            if response.status_code not in {
                500,
                502,
                503,
                504,
            }:
                return response

            if (
                attempt
                == max_attempts - 1
            ):
                return response

            delay = (
                retry_delays[
                    attempt
                ]
            )

            logger.warning(
                "Groq temporariamente "
                "indisponível "
                "status=%s "
                "tentativa=%s/%s "
                "retry_em=%ss",
                response.status_code,
                attempt + 1,
                max_attempts,
                delay,
            )

            time.sleep(delay)

        return last_response

    def _validate_http_response(
        self,
        response: httpx.Response,
    ):
        if response.status_code == 200:
            return

        # Provider error bodies may contain request data or credentials.
        logger.warning("Groq status=%s", response.status_code)

        code = {
            400: "GROQ_REQUEST_ERROR",
            401: "GROQ_AUTH_ERROR",
            403: "GROQ_AUTH_ERROR",
            404: "GROQ_MODEL_ERROR",
            429: "GROQ_RATE_LIMIT",
        }.get(
            response.status_code,
            "GROQ_UNAVAILABLE",
        )

        self.fail(code)

    def _extract_content(
        self,
        response: httpx.Response,
    ) -> str:
        try:
            content = (
                response.json()
                ["choices"][0]
                ["message"]
                ["content"]
            )

            if (
                not isinstance(
                    content,
                    str,
                )
                or not content.strip()
            ):
                raise ValueError()

            return content

        except (
            ValueError,
            KeyError,
            IndexError,
            TypeError,
        ):
            self.fail(
                "GROQ_INVALID_RESPONSE"
            )

    def assess_batch(
        self,
        batches,
    ):
        if not batches:
            return {}

        if not self._api_key():
            self.fail(
                "GROQ_CONFIG_ERROR"
            )

        claims_payload = []
        expected = {}

        for batch in batches:
            claim_index = (
                batch["claim_index"]
            )

            claim = batch["claim"]
            results = batch["results"]

            if not results:
                continue

            sources = [
                {
                    "evidence_index": (
                        evidence_index
                    ),
                    "title": (
                        result.title[:500]
                    ),
                    "snippet": (
                        result.snippet[:800]
                    ),
                }
                for evidence_index, result
                in enumerate(results)
            ]

            claims_payload.append(
                {
                    "claim_index": (
                        claim_index
                    ),
                    "claim": (
                        claim[:10000]
                    ),
                    "evidence": sources,
                }
            )

            expected[
                claim_index
            ] = {
                "results": results,
                "sources": sources,
            }

        if not claims_payload:
            return {}

        logger.info(
            "Groq fallback batch "
            "claims=%s",
            len(claims_payload),
        )

        payload = {
            "model": self.config.groq_model,

            "messages": [
                {
                    "role": "system",
                    "content": (
                        BATCH_INSTRUCTIONS
                        + "\n\n"
                        + "Retorne SOMENTE JSON válido. "
                        + "Preferencialmente use um objeto "
                        + "com a chave \"claims\"."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "claims": claims_payload,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],

            "temperature": 0,

            "reasoning_effort": "low",

            "include_reasoning": False,
        }

        response = self._request(
            payload
        )

        self._validate_http_response(
            response
        )

        content = self._extract_content(
            response
        )

        try:
            raw = json.loads(content)

            if isinstance(raw, list):
                logger.info(
                    "Groq root=array; normalizando."
                )
                raw = {
                    "claims": raw,
                }

            if not isinstance(raw, dict):
                logger.warning(
                    "Groq invalid_response reason=root_type"
                )
                raise ValueError()

            try:
                parsed = (
                    BatchAssessments
                    .model_validate(
                        raw
                    )
                )
            except Exception:
                logger.warning(
                    "Groq invalid_response reason=pydantic"
                )
                raise ValueError()

            returned_claim_indexes = sorted(
                claim.claim_index
                for claim
                in parsed.claims
            )

            expected_claim_indexes = sorted(
                expected.keys()
            )

            if (
                returned_claim_indexes
                != expected_claim_indexes
            ):
                logger.warning(
                    "Groq invalid_response "
                    "reason=claim_indexes"
                )
                raise ValueError()

            result = {}

            for claim_assessment in (
                parsed.claims
            ):
                claim_index = (
                    claim_assessment
                    .claim_index
                )

                claim_data = (
                    expected[
                        claim_index
                    ]
                )

                results = (
                    claim_data[
                        "results"
                    ]
                )

                sources = (
                    claim_data[
                        "sources"
                    ]
                )

                assessments = sorted(
                    claim_assessment.items,
                    key=lambda item: (
                        item.evidence_index
                    ),
                )

                indexes = [
                    item.evidence_index
                    for item
                    in assessments
                ]

                expected_indexes = list(
                    range(
                        len(results)
                    )
                )

                if (
                    indexes
                    != expected_indexes
                ):
                    logger.warning(
                        "Groq invalid_response "
                        "reason=evidence_indexes "
                        "claim_index=%s",
                        claim_index,
                    )
                    raise ValueError()

                converted = []

                for assessment in (
                    assessments
                ):
                    source = (
                        sources[
                            assessment
                            .evidence_index
                        ]
                    )

                    if (
                        assessment.verdict
                        != "NEUTRAL"
                    ):
                        quote = (
                            assessment
                            .quote
                            .strip()
                        )

                        if not quote:
                            logger.warning(
                                "Groq invalid_response "
                                "reason=empty_directional_quote "
                                "claim_index=%s "
                                "evidence_index=%s",
                                claim_index,
                                assessment.evidence_index,
                            )
                            raise ValueError()

                        quote_found = any(
                            quote
                            in source[field]
                            for field in (
                                "title",
                                "snippet",
                            )
                        )

                        if not quote_found:
                            logger.warning(
                                "Groq invalid_response "
                                "reason=quote_not_found "
                                "claim_index=%s "
                                "evidence_index=%s",
                                claim_index,
                                assessment.evidence_index,
                            )
                            raise ValueError()

                    converted.append(
                        Assessment(
                            index=(
                                assessment
                                .evidence_index
                            ),
                            verdict=(
                                assessment
                                .verdict
                            ),
                            relevance=(
                                assessment
                                .relevance
                            ),
                            quote=(
                                assessment
                                .quote
                            ),
                            reason=(
                                assessment
                                .reason
                            ),
                        )
                    )

                result[
                    claim_index
                ] = converted

            return result

        except (
            ValueError,
            KeyError,
            IndexError,
            TypeError,
            json.JSONDecodeError,
        ):
            self.fail(
                "GROQ_INVALID_RESPONSE"
            )

    @staticmethod
    def fail(code):
        logger.warning(
            "Groq code=%s",
            code,
        )

        messages = {
            "GROQ_AUTH_ERROR": (
                "A Groq recusou "
                "a autenticação."
            ),
            "GROQ_REQUEST_ERROR": (
                "A Groq rejeitou "
                "a solicitação."
            ),
            "GROQ_MODEL_ERROR": (
                "O modelo Groq configurado "
                "não está disponível."
            ),
            "GROQ_TIMEOUT": (
                "A Groq demorou demais "
                "para responder."
            ),
            "GROQ_CONNECTION_ERROR": (
                "Não foi possível conectar "
                "à Groq."
            ),
            "GROQ_INVALID_RESPONSE": (
                "A Groq respondeu, mas "
                "a resposta não passou "
                "na validação."
            ),
            "GROQ_UNAVAILABLE": (
                "A Groq está "
                "temporariamente "
                "indisponível."
            ),
            "GROQ_CONFIG_ERROR": (
                "A chave da Groq não "
                "está configurada."
            ),
            "GROQ_RATE_LIMIT": (
                "A Groq atingiu o "
                "limite gratuito de uso."
            ),
        }

        raise ExternalServiceException(
            message=messages.get(
                code,
                (
                    "Não foi possível "
                    "concluir a interpretação "
                    "pela Groq."
                ),
            ),
            code=code,
        ) from None
