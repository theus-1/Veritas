import json
from unittest.mock import Mock

import httpx
import pytest

from app.clients.groq_client import GroqClient
from app.core.config import Config
from app.core.exceptions import ExternalServiceException
from app.schemas.search import SearchResult


def batch():
    return [{'claim_index': 0, 'claim': 'Brasil venceu Argentina', 'results': [SearchResult(title='Brasil venceu Argentina', snippet='Brasil venceu Argentina', url='https://example.com', source_name='Fonte')]}]


def client():
    return GroqClient(Config(groq_api_key='dummy-test'))


def item():
    return dict(evidence_index=0, verdict='SUPPORTS', relevance=.95, quote='Brasil venceu Argentina', reason='O trecho apoia a afirmação.')


def response(value):
    return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(value)}}]})


@pytest.mark.parametrize('as_array', [False, True])
def test_valid_object_and_array(monkeypatch, as_array):
    claims = [{'claim_index': 0, 'items': [item()]}]
    monkeypatch.setattr(httpx, 'post', Mock(return_value=response(claims if as_array else {'claims': claims})))
    assert client().assess_batch(batch())[0][0].verdict == 'SUPPORTS'


@pytest.mark.parametrize('patch', [{'evidence_index': 2}, {'quote': 'invented'}, {'quote': ''}, {'relevance': 2}, {'reason': ''}, {'verdict': 'FALSE'}])
def test_invalid_assessment(monkeypatch, patch):
    monkeypatch.setattr(httpx, 'post', Mock(return_value=response({'claims': [{'claim_index': 0, 'items': [item() | patch]}]})))
    with pytest.raises(ExternalServiceException) as error:
        client().assess_batch(batch())
    assert error.value.code == 'GROQ_INVALID_RESPONSE'


@pytest.mark.parametrize('value', [None, {}, {'claims': []}, {'claims': [{'claim_index': 2, 'items': [item()]}]}])
def test_incomplete_batch(monkeypatch, value):
    monkeypatch.setattr(httpx, 'post', Mock(return_value=response(value)))
    with pytest.raises(ExternalServiceException) as error:
        client().assess_batch(batch())
    assert error.value.code == 'GROQ_INVALID_RESPONSE'


@pytest.mark.parametrize('status,code', [(400, 'GROQ_REQUEST_ERROR'), (401, 'GROQ_AUTH_ERROR'), (403, 'GROQ_AUTH_ERROR'), (404, 'GROQ_MODEL_ERROR'), (429, 'GROQ_RATE_LIMIT'), (503, 'GROQ_UNAVAILABLE')])
def test_http_errors_are_sanitized(monkeypatch, caplog, status, code):
    monkeypatch.setattr('app.clients.groq_client.time.sleep', lambda _: None)
    post = Mock(return_value=httpx.Response(status, json={'error': {'message': 'private-provider-body', 'type': 'private-type'}}))
    monkeypatch.setattr(httpx, 'post', post)
    with pytest.raises(ExternalServiceException) as error:
        client().assess_batch(batch())
    assert error.value.code == code
    assert 'private' not in caplog.text
    assert post.call_count == (2 if status == 503 else 1)


@pytest.mark.parametrize('failure,code', [(httpx.ReadTimeout, 'GROQ_TIMEOUT'), (httpx.ConnectError, 'GROQ_CONNECTION_ERROR')])
def test_transport(monkeypatch, failure, code):
    monkeypatch.setattr('app.clients.groq_client.time.sleep', lambda _: None)
    monkeypatch.setattr(httpx, 'post', Mock(side_effect=failure('private')))
    with pytest.raises(ExternalServiceException) as error:
        client().assess_batch(batch())
    assert error.value.code == code


def test_empty_and_unconfigured():
    assert client().assess_batch([]) == {}
    with pytest.raises(ExternalServiceException) as error:
        GroqClient(Config(groq_api_key='')).assess_batch(batch())
    assert error.value.code == 'GROQ_CONFIG_ERROR'
