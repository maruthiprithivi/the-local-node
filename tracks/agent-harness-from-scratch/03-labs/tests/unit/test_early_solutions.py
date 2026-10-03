"""The normal reference suite verifies the completed early implementation."""
import importlib.util
from pathlib import Path
import pytest

LABS = Path(__file__).resolve().parents[2]

def load_source(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

reference = load_source("early_harness_reference", LABS / "solutions" / "early_harness.py")
checks = load_source("early_harness_checks", LABS / "exercises" / "_checks.py")

@pytest.mark.parametrize("case", [
    checks.lesson_01_success, checks.lesson_01_edges,
    checks.lesson_05_success, checks.lesson_05_limits,
    checks.lesson_06_denied_and_approval, checks.lesson_06_exact_allowed_scope,
], ids=["lesson_01_success", "lesson_01_edges", "lesson_05_success",
        "lesson_05_limits", "lesson_06_denied", "lesson_06_exact_scope"])
def test_early_reference(case):
    case(reference)

