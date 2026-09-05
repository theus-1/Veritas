from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from threading import Lock

from app.core.exceptions import VeritasException


class RateLimiter:
    def __init__(
        self,
        max_per_minute: int = 5,
        max_per_hour: int = 30,
    ):
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour

        self.requests = defaultdict(deque)
        self.lock = Lock()

    def check(self, client_id: str):
        now = datetime.now(UTC)

        with self.lock:
            timestamps = self.requests[client_id]

            one_hour_ago = now - timedelta(hours=1)

            while timestamps and timestamps[0] < one_hour_ago:
                timestamps.popleft()

            minute_count = sum(
                1
                for timestamp in timestamps
                if timestamp >= now - timedelta(minutes=1)
            )

            hour_count = len(timestamps)

            if minute_count >= self.max_per_minute:
                raise VeritasException(
                    message=(
                        "Muitas análises foram solicitadas em pouco tempo. "
                        "Tente novamente em alguns instantes."
                    ),
                    status_code=429,
                    code="RATE_LIMIT_MINUTE",
                )

            if hour_count >= self.max_per_hour:
                raise VeritasException(
                    message=(
                        "O limite de análises por hora foi atingido. "
                        "Tente novamente mais tarde."
                    ),
                    status_code=429,
                    code="RATE_LIMIT_HOUR",
                )

            timestamps.append(now)


analysis_rate_limiter = RateLimiter(
    max_per_minute=5,
    max_per_hour=30,
)
