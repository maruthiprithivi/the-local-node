from course_harness.observability import TraceSink, UsageLedger


def test_lesson_20_redaction_bounds_correlation_and_unknown_usage():
    sink = TraceSink(run_id="r", task_id="t", secrets=("synthetic-secret",), max_events=2)
    sink.emit("request", api_key="synthetic-secret", observation="synthetic-secret", run_id="spoofed")
    sink.emit("tool", call_id="c")
    sink.emit("overflow")
    assert sink.events[0]["run_id"] == "r"
    assert "synthetic-secret" not in str(sink.events)
    assert sink.dropped == 1
    ledger = UsageLedger()
    ledger.record({"input_tokens": 10, "output_tokens": 2})
    ledger.record({}, retried=True)
    assert ledger.retries == 1
    assert ledger.estimate(input_per_million=1, output_per_million=2)["estimated_cost"] is None
