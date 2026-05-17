from app.alerts.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


def test_circuit_opens_after_failures():
    breaker = CircuitBreaker("test", failure_threshold=2, recovery_timeout=60)

    def fail():
        raise RuntimeError("boom")

    for _ in range(2):
        try:
            breaker.call(fail)
        except RuntimeError:
            pass

    assert breaker.state == CircuitState.OPEN
    try:
        breaker.call(lambda: "ok")
        raise AssertionError("expected CircuitOpenError")
    except CircuitOpenError:
        pass


def test_circuit_recovers_on_success():
    breaker = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0)

    try:
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("x")))
    except RuntimeError:
        pass

    breaker.recovery_timeout = 0
    result = breaker.call(lambda: "recovered")
    assert result == "recovered"
    assert breaker.state == CircuitState.CLOSED
