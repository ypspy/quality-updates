from pathlib import Path


def test_summarize_skill_calls_the_record_writer():
    skill = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "quality-updates-writer" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    assert "python scripts/write_quarterly_record.py" in text
    assert "--append-facts" in text
    assert "--append-minutes" in text
    assert "data/quarterly-processed/" in text
