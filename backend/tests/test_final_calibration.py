from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.exceptions import ExternalServiceException
from app.services.analysis_service import AnalysisService
from app.services.evidence_service import EvidenceService
from app.schemas.search import SearchResult


@pytest.mark.parametrize('direction', ['SUPPORTS', 'CONTRADICTS'])
def test_extreme_relevance_does_not_imply_near_certainty(direction):
    service = AnalysisService()
    confidence = []
    for count in range(1, 6):
        votes = [SimpleNamespace(relevance=EvidenceService.calibrate_relevance(1), verdict=direction, source_name=str(i), claim_id='a') for i in range(count)]
        confidence.append(service.calculate_confidence(votes))
        assert service.calculate_confidence(votes * 4) == confidence[-1]
    assert confidence == sorted(confidence)
    assert confidence[-1] < .9


def test_relevance_preserves_thresholds_and_compresses_tail():
    values = [EvidenceService.calibrate_relevance(x) for x in [0, .19, .2, .8, .9, .95, 1]]
    assert values == [0, .19, .2, .8, .9, .91, .92]
    result = SearchResult(title='Brasil venceu Argentina', snippet='Brasil venceu Argentina', url='https://example.com', source_name='Fonte')
    assert EvidenceService().calculate_relevance(result.title, result) == .92


def test_gemini_remains_primary():
    service = AnalysisService()
    service.config.gemini_enabled = True
    service.gemini_client.assess_batch = Mock(return_value={0: 'assessment'})
    service.groq_client.assess_batch = Mock()
    assert service._assess_batch_with_fallback([]) == {0: 'assessment'}
    service.groq_client.assess_batch.assert_not_called()


def test_groq_invalid_batch_falls_back_locally():
    service = AnalysisService()
    service.config.gemini_enabled = True
    service.config.groq_api_key = 'dummy-test'
    service.gemini_client.assess_batch = Mock(side_effect=ExternalServiceException(message='Unavailable', code='GEMINI_RATE_LIMIT'))
    service.groq_client.assess_batch = Mock(side_effect=ExternalServiceException(message='Invalid', code='GROQ_INVALID_RESPONSE'))
    assert service._assess_batch_with_fallback([]) == {}
    service.gemini_client.assess_batch.assert_called_once()
    service.groq_client.assess_batch.assert_called_once()
