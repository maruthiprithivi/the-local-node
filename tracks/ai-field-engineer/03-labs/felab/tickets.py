"""
felab.tickets — load the triage dataset and grade answers (lessons 07–11).

Three graders, from cheapest to most expensive — the eval pattern you'll pitch:
  1. parses   : is it JSON at all?
  2. valid    : does it match the schema (right keys, allowed enum, int in range)?
  3. correct  : does category (and severity) match the label?
(Lesson 09 adds a 4th: an LLM judge with a rubric, for fields with no single right answer.)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .targets import REPO_ROOT

DATA = REPO_ROOT / "data"
SCHEMA = json.loads((DATA / "triage_schema.json").read_text())
SYSTEM = ("You triage customer support tickets. Reply with JSON only: "
          '{"category": "billing|outage|how-to|abuse", "severity": 1-5, "next_action": "<short>"}')


def load_test(n: int | None = None) -> list[dict]:
    """Held-out tickets with labels. Run `python data/make_tickets.py` if missing."""
    path = DATA / "tickets" / "test.jsonl"
    if not path.exists():
        raise SystemExit("data/tickets/test.jsonl missing — run: python data/make_tickets.py")
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return rows[:n] if n else rows


def parse(text: str | None) -> dict | None:
    """Strict: the reply must BE a JSON object (whitespace and ```json fences tolerated).
    Being lenient here would hide exactly the failures an integration breaks on."""
    if not text:
        return None
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def schema_valid(obj: dict | None) -> bool:
    if obj is None:
        return False
    try:
        import jsonschema
        jsonschema.validate(obj, SCHEMA)
        return True
    except ImportError:  # minimal fallback check
        return (obj.get("category") in SCHEMA["properties"]["category"]["enum"]
                and isinstance(obj.get("severity"), int) and 1 <= obj["severity"] <= 5
                and isinstance(obj.get("next_action"), str))
    except Exception:
        return False


def grade(reply: str | None, row: dict) -> dict:
    obj = parse(reply)
    return {
        "parses": obj is not None,
        "valid": schema_valid(obj),
        "category_ok": bool(obj) and obj.get("category") == row["category"],
        "severity_ok": bool(obj) and obj.get("severity") == row["severity"],
    }
