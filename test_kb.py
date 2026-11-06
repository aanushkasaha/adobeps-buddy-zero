import json
import re
import pytest


def load_kb():
    with open("kb.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_courses():
    return load_kb().get("courses", [])


def load_rules():
    return load_kb().get("rules", [])


def test_unique_course_codes():
    courses = load_courses()
    codes = [c.get("code") for c in courses]
    assert len(codes) == len(set(codes)), "Duplicate course codes found"


def test_course_schema_and_values():
    courses = load_courses()
    assert len(courses) > 0, "No courses found in kb.json"

    required_keys = {
        "code",
        "title",
        "ltpc",
        "credits",
        "cse_semester",
        "prerequisites",
        "prerequisites_stated",
        "skills",
        "source",
    }

    for course in courses:
        code = course.get("code", "<unknown>")

        # 1. Required keys exist
        missing = required_keys - set(course.keys())
        assert not missing, f"Course {code} missing keys: {missing}"

        # 2. Code matches two capital letters followed by four digits
        assert re.match(r"^[A-Z]{2}[0-9]{4}$", course["code"]), (
            f"Invalid course code format in {code}"
        )

        # 3. Last number in ltpc equals credits
        ltpc_parts = course["ltpc"].split("-")
        assert len(ltpc_parts) == 4, f"Invalid LTPC format: {course['ltpc']}"
        assert float(ltpc_parts[-1]) == float(course["credits"]), (
            f"Credits mismatch in {code}: ltpc={course['ltpc']}, credits={course['credits']}"
        )

        # 4. Credits == L + T + P/2
        l, t, p, _ = map(float, ltpc_parts)
        expected_credits = l + t + p / 2.0
        assert float(course["credits"]) == expected_credits, (
            f"Credits formula mismatch in {code}: {l} + {t} + {p}/2 = {expected_credits} != {course['credits']}"
        )

        # 5. prerequisites is list, prerequisites_stated is bool; if false, prerequisites is empty
        assert isinstance(course["prerequisites"], list), (
            f"prerequisites must be list in {code}"
        )
        assert isinstance(course["prerequisites_stated"], bool), (
            f"prerequisites_stated must be bool in {code}"
        )
        if not course["prerequisites_stated"]:
            assert len(course["prerequisites"]) == 0, (
                f"prerequisites must be empty when prerequisites_stated is False in {code}"
            )

        # 6. cse_semester is an integer from 1 to 8
        assert isinstance(course["cse_semester"], int), (
            f"cse_semester must be an integer in {code}"
        )
        assert 1 <= course["cse_semester"] <= 8, (
            f"cse_semester out of range 1-8 in {code}: {course['cse_semester']}"
        )

        # 7. skills is a non-empty list of strings
        assert isinstance(course["skills"], list) and len(course["skills"]) > 0, (
            f"skills must be a non-empty list in {code}"
        )
        assert all(isinstance(s, str) and len(s.strip()) > 0 for s in course["skills"]), (
            f"skills must be non-empty strings in {code}"
        )

        # 8. source starts with https://academics.iitp.ac.in/
        assert isinstance(course["source"], str) and course["source"].startswith(
            "https://academics.iitp.ac.in/"
        ), f"source must start with https://academics.iitp.ac.in/ in {code}"


def test_rules_exist_and_unique_ids():
    kb = load_kb()
    assert "rules" in kb, "'rules' key missing from kb.json"
    rules = kb["rules"]
    assert isinstance(rules, list), "'rules' must be a list"
    assert len(rules) > 0, "'rules' must be a non-empty list"

    rule_ids = [r.get("id") for r in rules]
    assert len(rule_ids) == len(set(rule_ids)), f"Duplicate rule IDs found: {rule_ids}"


def test_rule_schema_and_provenance():
    kb = load_kb()
    assert "rules" in kb, "'rules' key missing from kb.json"
    rules = kb["rules"]
    assert isinstance(rules, list) and len(rules) > 0, "'rules' must be a non-empty list"

    required_rule_keys = {"id", "title", "text", "source", "provenance"}

    for rule in rules:
        rule_id = rule.get("id", "<unknown>")
        missing = required_rule_keys - set(rule.keys())
        assert not missing, f"Rule {rule_id} missing keys: {missing}"

        source = rule.get("source")
        provenance = rule.get("provenance")

        valid_source = isinstance(source, str) and source.startswith(
            "https://academics.iitp.ac.in/"
        )
        valid_provenance = provenance == "student-reported"

        assert valid_source or valid_provenance, (
            f"Rule {rule_id} must have source starting with https://academics.iitp.ac.in/ "
            f"or provenance 'student-reported' (source={source!r}, provenance={provenance!r})"
        )
