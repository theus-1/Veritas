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


class OpenAIClient:
    REQUEST_TIMEOUT = 90.0
    CONNECT_TIMEOUT = 10.0

    MODEL = "gpt-5.6-luna"

    ENDPOINT = (
        "https://api.openai.com/v1/responses"
    )

    def __init__(self, config):
        self.config = config

    def _api_key(self) -> str:
        return (
            getattr(
                self.config,
                "openai_api_key",
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
        last_timeout = False

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
                last_timeout = False

            except httpx.TimeoutException:
                last_timeout = True

                if (
                    attempt
                    == max_attempts - 1
                ):
                    self.fail(
                        "OPENAI_TIMEOUT"
                    )

                delay = (
                    retry_delays[
                        attempt
                    ]
                )

                logger.warning(
                    "OpenAI timeout "
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
                    "OPENAI_CONNECTION_ERROR"
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
                "OpenAI temporariamente "
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

        if last_timeout:
            self.fail(
                "OPENAI_TIMEOUT"
            )

        return last_response

    def _validate_http_response(
        self,
        response: httpx.Response,
    ):
        if response.status_code == 200:
            return

        logger.warning(
            "OpenAI status=%s",
            response.status_code,
        )

        code = {
            400: "OPENAI_REQUEST_ERROR",
            401: "OPENAI_AUTH_ERROR",
            403: "OPENAI_AUTH_ERROR",
            404: "OPENAI_MODEL_ERROR",
            429: "OPENAI_RATE_LIMIT",
        }.get(
            response.status_code,
            "OPENAI_UNAVAILABLE",
        )

        self.fail(code)

    def _extract_content(
        self,
        response: httpx.Response,
    ) -> str:
        try:
            body = response.json()

            output = body["output"]

            for item in output:
                if (
                    item.get("type")
                    != "message"
                ):
                    continue

                for content in (
                    item.get(
                        "content",
                        []
                    )
                ):
                    text = content.get(
                        "text"
                    )

                    if (
                        isinstance(
                            text,
                            str,
                        )
                        and text.strip()
                    ):
                        return text

            raise ValueError()

        except (
            ValueError,
            KeyError,
            IndexError,
            TypeError,
        ):
            self.fail(
                "OPENAI_INVALID_RESPONSE"
            )

    def assess_batch(
        self,
        batches,
    ):
        if not batches:
            return {}

        if not self._api_key():
            self.fail(
                "OPENAI_CONFIG_ERROR"
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
            "OpenAI fallback batch "
            "claims=%s",
            len(claims_payload),
        )

        payload = {
            "model": self.MODEL,

            "reasoning": {
                "effort": "low",
            },

            "input": [
                {
                    "role": "system",
                    "content": (
                        BATCH_INSTRUCTIONS
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "claims": (
                                claims_payload
                            ),
                        },
                        ensure_ascii=False,
                    ),
                },
            ],

            "text": {
                "format": {
                    "type": "json_schema",
                    "name": (
                        "veritas_assessments"
                    ),
                    "strict": True,
                    "schema": (
                        BatchAssessments
                        .model_json_schema()
                    ),
                }
            },

            "max_output_tokens": 4096,
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
            parsed = (
                BatchAssessments
                .model_validate_json(
                    content
                )
            )

            returned_claim_indexes = sorted(
                claim.claim_index
                for claim in parsed.claims
            )

            expected_claim_indexes = sorted(
                expected.keys()
            )

            if (
                returned_claim_indexes
                != expected_claim_indexes
            ):
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
                        if (
                            not assessment
                            .quote
                            .strip()
                        ):
                            raise ValueError()

                        quote_found = any(
                            assessment.quote
                            in source[field]
                            for field in (
                                "title",
                                "snippet",
                            )
                        )

                        if not quote_found:
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
        ):
            self.fail(
                "OPENAI_INVALID_RESPONSE"
            )

    @staticmethod
    def fail(code):
        logger.warning(
            "OpenAI code=%s",
            code,
        )

        messages = {
            "OPENAI_AUTH_ERROR": (
                "A OpenAI recusou a "
                "autenticação ou o acesso."
            ),
            "OPENAI_REQUEST_ERROR": (
                "A OpenAI rejeitou o "
                "formato da solicitação."
            ),
            "OPENAI_MODEL_ERROR": (
                "O modelo OpenAI "
                "configurado não foi "
                "encontrado."
            ),
            "OPENAI_TIMEOUT": (
                "A OpenAI demorou demais "
                "para responder."
            ),
            "OPENAI_CONNECTION_ERROR": (
                "Não foi possível conectar "
                "à OpenAI."
            ),
            "OPENAI_INVALID_RESPONSE": (
                "A OpenAI respondeu, mas "
                "a resposta não passou "
                "na validação."
            ),
            "OPENAI_UNAVAILABLE": (
                "O serviço OpenAI está "
                "temporariamente "
                "indisponível."
            ),
            "OPENAI_CONFIG_ERROR": (
                "A chave da OpenAI não "
                "está configurada."
            ),
            "OPENAI_RATE_LIMIT": (
                "A OpenAI atingiu o "
                "limite de uso."
            ),
        }

        raise ExternalServiceException(
            message=messages.get(
                code,
                (
                    "Não foi possível "
                    "concluir a interpretação "
                    "pela OpenAI."
                ),
            ),
            code=code,
        ) from None
