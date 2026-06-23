import pytest

from shared.retry import retry, RetryError


def test_succeeds_without_retry():
    calls = []

    @retry(attempts=3, sleep=lambda _: None)
    def ok():
        calls.append(1)
        return "done"

    assert ok() == "done"
    assert len(calls) == 1


def test_retries_then_succeeds():
    calls = {"n": 0}

    @retry(attempts=3, sleep=lambda _: None, exceptions=(ConnectionError,))
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transient")
        return "recovered"

    assert flaky() == "recovered"
    assert calls["n"] == 3


def test_raises_retryerror_after_exhausting_attempts():
    @retry(attempts=2, sleep=lambda _: None, exceptions=(TimeoutError,))
    def always_fails():
        raise TimeoutError("nope")

    with pytest.raises(RetryError) as exc:
        always_fails()
    assert exc.value.attempts == 2
    assert isinstance(exc.value.last_exc, TimeoutError)


def test_non_listed_exception_propagates_immediately():
    calls = {"n": 0}

    @retry(attempts=3, sleep=lambda _: None, exceptions=(ConnectionError,))
    def wrong_error():
        calls["n"] += 1
        raise ValueError("not retryable")

    with pytest.raises(ValueError):
        wrong_error()
    assert calls["n"] == 1  # not retried
