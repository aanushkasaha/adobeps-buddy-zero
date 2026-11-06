import json
import pytest


def load_targets():
    with open("targets.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_profile():
    with open("profile.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_kb():
    with open("kb.json", "r", encoding="utf-8") as f:
        return json.load(f)


def test_targets_schema_and_uniqueness():
    data = load_targets()
    assert "depth_levels" in data, "targets.json missing 'depth_levels'"
    assert "targets" in data, "targets.json missing 'targets'"

    depth_levels = set(data["depth_levels"])
    targets = data["targets"]

    # Target ids are unique
    target_ids = [t.get("id") for t in targets]
    assert len(target_ids) == len(set(target_ids)), "Duplicate target IDs found in targets.json"

    # kb.json course codes for defined_by check
    kb_data = load_kb()
    valid_course_codes = {c["code"] for c in kb_data.get("courses", [])}

    for t in targets:
        tid = t.get("id", "<unknown>")
        # Every required_depth is in depth_levels
        assert t.get("required_depth") in depth_levels, (
            f"Target {tid} has required_depth '{t.get('required_depth')}' not in depth_levels"
        )

        # Every defined_by is null or a course code that exists in kb.json
        defined_by = t.get("defined_by")
        assert defined_by is None or defined_by in valid_course_codes, (
            f"Target {tid} has defined_by '{defined_by}' which does not exist in kb.json"
        )


def test_facts_schema_and_rules():
    targets_data = load_targets()
    depth_levels = set(targets_data.get("depth_levels", []))
    target_ids = {t["id"] for t in targets_data.get("targets", [])}

    profile_data = load_profile()
    assert "facts" in profile_data, "profile.json missing 'facts'"
    facts = profile_data["facts"]

    # Fact ids are unique
    fact_ids = [f.get("id") for f in facts]
    assert len(fact_ids) == len(set(fact_ids)), "Duplicate fact IDs found in profile.json"

    required_keys = {"id", "topic", "claim", "depth", "source", "trust", "evidence"}
    valid_sources = {"graded", "tested", "self_declared"}
    valid_trusts = {"high", "medium", "low"}

    for f in facts:
        fid = f.get("id", "<unknown>")

        # Every fact has id, topic, claim, depth, source, trust, evidence
        missing = required_keys - set(f.keys())
        assert not missing, f"Fact {fid} missing keys: {missing}"

        # Every fact's topic must be either an id in targets.json or exactly 'programming.c'
        topic = f.get("topic")
        assert topic in target_ids or topic == "programming.c", (
            f"Fact {fid} topic '{topic}' is neither in targets.json nor 'programming.c'"
        )

        # Fact depth is in depth_levels
        assert f.get("depth") in depth_levels, (
            f"Fact {fid} depth '{f.get('depth')}' not in depth_levels"
        )

        # Source is one of graded, tested, self_declared
        assert f.get("source") in valid_sources, (
            f"Fact {fid} source '{f.get('source')}' invalid"
        )

        # Trust is one of high, medium, low
        assert f.get("trust") in valid_trusts, (
            f"Fact {fid} trust '{f.get('trust')}' invalid"
        )

        # A self_declared fact never has trust 'high'
        if f.get("source") == "self_declared":
            assert f.get("trust") != "high", (
                f"Fact {fid} is self_declared but has trust 'high'"
            )

        # Graded and tested facts have a non-empty evidence string
        if f.get("source") in {"graded", "tested"}:
            evidence = f.get("evidence")
            assert isinstance(evidence, str) and len(evidence.strip()) > 0, (
                f"Fact {fid} has source '{f.get('source')}' but empty evidence"
            )
