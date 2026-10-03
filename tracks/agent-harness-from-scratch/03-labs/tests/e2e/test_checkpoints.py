import pytest

from course_harness.__main__ import checkpoint, conversation


@pytest.mark.parametrize("lesson", range(33), ids=[f"lesson_{i:02}" for i in range(33)])
@pytest.mark.parametrize("scenario", ["coding", "sre", "automation"])
def test_checkpoints(lesson, scenario):
    result = checkpoint(lesson, scenario)
    assert result["status"] == "ok", result
    assert result["checks"] and all(result["checks"].values())


def test_lesson_02_conversation_reset_exit():
    lines = iter(["hello", "/reset", "again", "/exit"])
    output = []
    conversation(lambda _: next(lines), output.append)
    assert "session reset" in output
    assert output[-1] == "bye"


def test_lesson_02_eof():
    def eof(_):
        raise EOFError
    output = []
    conversation(eof, output.append)
    assert output[-1] == "bye"
