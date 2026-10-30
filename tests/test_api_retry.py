"""Fast offline tests for the API retry policy (no Gemini calls)."""
import pytest

from services.api_retry_service import api_error_status, call_with_retry


class FakeApiError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(f"HTTP {code}")


def _wrapped_error(code):
    try:
        raise FakeApiError(code)
    except FakeApiError as err:
        try:
            raise RuntimeError("Gemini Batch Generator: błąd API") from err
        except RuntimeError as wrapped:
            return wrapped


def test_wrapped_status_detection():
    assert api_error_status(_wrapped_error(503)) == 503
    assert api_error_status(RuntimeError("503 without HTTP status")) is None


def test_503_retries_then_succeeds():
    attempts = []
    waits = []

    def operation():
        attempts.append(1)
        if len(attempts) < 3:
            raise _wrapped_error(503)
        return "OK"

    assert call_with_retry(
        operation, sleep=waits.append, jitter_fn=lambda a, b: 0.0,
    ) == "OK"
    assert len(attempts) == 3
    assert waits == [3.0, 6.0]


def test_429_retries():
    counter = 0

    def operation():
        nonlocal counter
        counter += 1
        if counter == 1:
            raise _wrapped_error(429)
        return 12

    assert call_with_retry(operation, sleep=lambda _: None) == 12
    assert counter == 2


def test_final_503_preserves_original_exception():
    counter = 0

    def operation():
        nonlocal counter
        counter += 1
        raise _wrapped_error(503)

    with pytest.raises(RuntimeError, match="błąd API") as err:
        call_with_retry(operation, sleep=lambda _: None)
    assert counter == 3
    assert isinstance(err.value.__cause__, FakeApiError)


def test_400_not_retried():
    counter = 0

    def operation():
        nonlocal counter
        counter += 1
        raise _wrapped_error(400)

    with pytest.raises(RuntimeError):
        call_with_retry(operation, sleep=lambda _: None)
    assert counter == 1


def test_non_api_error_not_retried():
    counter = 0

    def operation():
        nonlocal counter
        counter += 1
        raise ValueError("Bad slide JSON")

    with pytest.raises(ValueError):
        call_with_retry(operation, sleep=lambda _: None)
    assert counter == 1


def test_delay_capped_and_jitter():
    waits = []
    calls = 0

    def operation():
        nonlocal calls
        calls += 1
        raise FakeApiError(503)

    with pytest.raises(FakeApiError):
        call_with_retry(
            operation, attempts=4, initial_delay=5, max_delay=8,
            jitter=1, jitter_fn=lambda a, b: b, sleep=waits.append,
        )
    assert calls == 4
    assert waits == [6, 8, 8]


def test_invalid_attempts():
    with pytest.raises(ValueError):
        call_with_retry(lambda: "no", attempts=0)
