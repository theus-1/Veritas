import pytest

from app.core.exceptions import VeritasException
from app.core.rate_limit import RateLimiter


def test_rate_limiter_allows_requests_under_limit():
    limiter = RateLimiter(
        max_per_minute=5,
        max_per_hour=30,
    )

    for _ in range(5):
        limiter.check("127.0.0.1")


def test_rate_limiter_blocks_minute_limit():
    limiter = RateLimiter(
        max_per_minute=2,
        max_per_hour=30,
    )

    limiter.check("127.0.0.1")
    limiter.check("127.0.0.1")

    with pytest.raises(VeritasException) as exc_info:
        limiter.check("127.0.0.1")

    assert exc_info.value.status_code == 429
    assert exc_info.value.code == "RATE_LIMIT_MINUTE"


def test_rate_limiter_separates_clients():
    limiter = RateLimiter(
        max_per_minute=1,
        max_per_hour=30,
    )

    limiter.check("client-a")
    limiter.check("client-b")

    with pytest.raises(VeritasException):
        limiter.check("client-a")


def test_rate_limiter_blocks_hour_limit():
    limiter = RateLimiter(
        max_per_minute=100,
        max_per_hour=2,
    )

    limiter.check("127.0.0.1")
    limiter.check("127.0.0.1")

    with pytest.raises(VeritasException) as exc_info:
        limiter.check("127.0.0.1")

    assert exc_info.value.status_code == 429
    assert exc_info.value.code == "RATE_LIMIT_HOUR"
