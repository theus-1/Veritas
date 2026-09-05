import json
from unittest.mock import Mock
from types import SimpleNamespace
import httpx
import time
import pytest
from app.clients.gemini_client import GeminiClient
from app.core.config import Config
from app.core.exceptions import ExternalServiceException
from app.schemas.search import SearchResult
from app.clients.gemini_client import Assessment
from app.services.evidence_service import EvidenceService


def result():
    return SearchResult(title="É falso que houve invasão", snippet="A urna não foi invadida.", url="https://example.com", source_name="Fonte")


def item():
    return dict(index=0, verdict="CONTRADICTS", relevance=0.9, quote="A urna não foi invadida.", reason="O texto desmente a invasão.")


def response(items, finish="STOP"):
    return httpx.Response(200, json={"candidates": [{"finishReason": finish, "content": {"parts": [{"text": json.dumps({"items": items})}]}}]})


def test_request_and_validated_response(monkeypatch, caplog):
    post = Mock(return_value=response([item()]))
    monkeypatch.setattr(httpx, "post", post)
    client = GeminiClient(Config())
    assert client.assess("Houve invasão", [result()])[0].verdict == "CONTRADICTS"
    args, kwargs = post.call_args
    assert "dummy-gemini" not in args[0]
    assert kwargs["headers"]["x-goog-api-key"] == "dummy-gemini"
    timeout = kwargs["timeout"]

    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == 10.0
    assert timeout.read == 90.0
    assert "dummy-gemini" not in caplog.text

    payload = kwargs["json"]

    assert (
        payload["generationConfig"]["thinkingConfig"]["thinkingLevel"]
        == "LOW"
    )

    assert payload["generationConfig"]["maxOutputTokens"] == 4096
    assert "temperature" not in payload["generationConfig"]


@pytest.mark.parametrize("status,code", [(400,"GEMINI_REQUEST_ERROR"),(404,"GEMINI_MODEL_ERROR"),(401,"GEMINI_AUTH_ERROR"),(403,"GEMINI_AUTH_ERROR"),(429,"GEMINI_RATE_LIMIT")])
def test_errors_no_retry(monkeypatch, status, code):
    post = Mock(return_value=httpx.Response(status, text="private"))
    monkeypatch.setattr(httpx, "post", post)
    with pytest.raises(ExternalServiceException) as error:
        GeminiClient(Config()).assess("claim", [result()])
    assert error.value.code == code
    assert "private" not in str(error.value)
    assert post.call_count == 1


@pytest.mark.parametrize("patch", [{"index":1},{"quote":"invented"},{"verdict":"FALSE"},{"relevance":2},{"reason":""}])
def test_invalid_assessment_rejected(monkeypatch, patch):
    value = item() | patch
    monkeypatch.setattr(httpx, "post", lambda *a, **k: response([value]))
    with pytest.raises(ExternalServiceException) as error:
        GeminiClient(Config()).assess("claim", [result()])
    assert error.value.code == "GEMINI_INVALID_RESPONSE"


@pytest.mark.parametrize("payload", [response([]), response([item(),item()]), response([item()], "MAX_TOKENS"), httpx.Response(200,json={}), httpx.Response(200,text="bad")])
def test_incomplete_output_rejected(monkeypatch, payload):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: payload)
    with pytest.raises(ExternalServiceException):
        GeminiClient(Config()).assess("claim", [result()])


@pytest.mark.parametrize("failure,code", [(httpx.ReadTimeout,"GEMINI_TIMEOUT"),(httpx.ConnectError,"GEMINI_CONNECTION_ERROR")])
def test_transport(monkeypatch, failure, code):
    monkeypatch.setattr(httpx,"post",Mock(side_effect=failure("private")))
    with pytest.raises(ExternalServiceException) as error:
        GeminiClient(Config()).assess("claim",[result()])
    assert error.value.code == code


def test_empty_and_missing_key():
    assert GeminiClient(Config()).assess("claim",[]) == []
    with pytest.raises(ExternalServiceException) as error:
        GeminiClient(Config(gemini_api_key=" ")).assess("claim",[result()])
    assert error.value.code == "GEMINI_CONFIG_ERROR"


def test_service_uses_ai_and_persists_reason():
    analysis = SimpleNamespace(
        id=1,
        explanation=None,
    )

    assessments = [
        Assessment(
            index=0,
            verdict="CONTRADICTS",
            relevance=0.9,
            quote="Houve invasão",
            reason="A evidência contradiz a afirmação.",
        )
    ]

    values = EvidenceService().create_evidences(
        Mock(),
        analysis,
        SimpleNamespace(
            id=1,
            text="Houve invasão",
        ),
        [result()],
        assessments=assessments,
    )

    assert values[0].verdict == "CONTRADICTS"
    assert values[0].relevance == 0.9

    assert (
    values[0].reason
    == "A evidência contradiz a afirmação."
)

def test_diagnostics_do_not_log_provider_body_or_key(monkeypatch, caplog):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(400, text="sensitive-provider-body dummy-gemini"))
    with pytest.raises(ExternalServiceException):
        GeminiClient(Config()).assess("private-claim", [result()])
    assert "Gemini status=400" in caplog.text
    assert "Gemini code=GEMINI_REQUEST_ERROR" in caplog.text
    assert "sensitive-provider-body" not in caplog.text
    assert "dummy-gemini" not in caplog.text
    assert "private-claim" not in caplog.text

def test_server_error_retries_three_times(monkeypatch):
    post = Mock(
        return_value=httpx.Response(
            500,
            text="private",
        )
    )

    monkeypatch.setattr(
        httpx,
        "post",
        post,
    )

    monkeypatch.setattr(
        time,
        "sleep",
        lambda *_: None,
    )

    with pytest.raises(
        ExternalServiceException
    ) as error:
        GeminiClient(
            Config()
        ).assess(
            "claim",
            [result()],
        )

    assert (
        error.value.code
        == "GEMINI_UNAVAILABLE"
    )

    assert "private" not in str(
        error.value
    )

    assert post.call_count == 3

def test_connection_error_no_retry(
    monkeypatch,
):
    post = Mock(
        side_effect=httpx.ConnectError(
            "connection failed"
        )
    )

    monkeypatch.setattr(
        httpx,
        "post",
        post,
    )

    with pytest.raises(
        ExternalServiceException
    ) as error:
        GeminiClient(
            Config()
        ).assess(
            "claim",
            [result()],
        )

    assert (
        error.value.code
        == "GEMINI_CONNECTION_ERROR"
    )

    assert post.call_count == 1

def test_timeout_retries_three_times(
    monkeypatch,
):
    post = Mock(
        side_effect=httpx.ReadTimeout(
            "timeout"
        )
    )

    monkeypatch.setattr(
        httpx,
        "post",
        post,
    )

    monkeypatch.setattr(
        time,
        "sleep",
        lambda *_: None,
    )

    with pytest.raises(
        ExternalServiceException
    ) as error:
        GeminiClient(
            Config()
        ).assess(
            "claim",
            [result()],
        )

    assert (
        error.value.code
        == "GEMINI_TIMEOUT"
    )

    assert post.call_count == 3

def test_retry_503_timeout_then_success(
    monkeypatch,
):
    success_body = {
        "candidates": [
            {
                "finishReason": "STOP",
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "items": [
                                        {
                                            "index": 0,
                                            "verdict": (
                                                "NEUTRAL"
                                            ),
                                            "relevance": (
                                                0.5
                                            ),
                                            "quote": "",
                                            "reason": (
                                                "Evidência "
                                                "insuficiente."
                                            ),
                                        }
                                    ]
                                }
                            )
                        }
                    ]
                },
            }
        ]
    }

    responses = [
        httpx.Response(
            503,
            text="temporary",
        ),
        httpx.ReadTimeout(
            "timeout"
        ),
        httpx.Response(
            200,
            json=success_body,
        ),
    ]

    def fake_post(
        *args,
        **kwargs,
    ):
        value = responses.pop(0)

        if isinstance(
            value,
            Exception,
        ):
            raise value

        return value

    post = Mock(
        side_effect=fake_post
    )

    monkeypatch.setattr(
        httpx,
        "post",
        post,
    )

    monkeypatch.setattr(
        time,
        "sleep",
        lambda *_: None,
    )

    assessments = (
        GeminiClient(
            Config()
        )
        .assess(
            "claim",
            [result()],
        )
    )

    assert len(assessments) == 1

    assert (
        assessments[0].verdict
        == "NEUTRAL"
    )

    assert (
        assessments[0].relevance
        == 0.5
    )

    assert post.call_count == 3

def test_retry_503_then_success(
    monkeypatch,
):
    success_body = {
        "candidates": [
            {
                "finishReason": "STOP",
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "items": [
                                        {
                                            "index": 0,
                                            "verdict": (
                                                "SUPPORTS"
                                            ),
                                            "relevance": (
                                                0.9
                                            ),
                                            "quote": (
                                                "É falso que houve invasão"
                                            ),
                                            "reason": (
                                                "A evidência "
                                                "confirma."
                                            ),
                                        }
                                    ]
                                }
                            )
                        }
                    ]
                },
            }
        ]
    }

    post = Mock(
        side_effect=[
            httpx.Response(
                503,
                text="temporary",
            ),
            httpx.Response(
                503,
                text="temporary",
            ),
            httpx.Response(
                200,
                json=success_body,
            ),
        ]
    )

    monkeypatch.setattr(
        httpx,
        "post",
        post,
    )

    monkeypatch.setattr(
        time,
        "sleep",
        lambda *_: None,
    )

    assessments = (
        GeminiClient(
            Config()
        )
        .assess(
            "claim",
            [
                result(
                )
            ],
        )
    )

    assert len(assessments) == 1

    assert (
        assessments[0].verdict
        == "SUPPORTS"
    )

    assert post.call_count == 3
