import json
import re
import pytest


def load_courses():
    with open("kb.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("courses", [])


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

        # 4. prerequisites is list, prerequisites_stated is bool; if false, prerequisites is empty
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

        # 5. cse_semester is an integer from 1 to 8
        assert isinstance(course["cse_semester"], int), (
            f"cse_semester must be an integer in {code}"
        )
        assert 1 <= course["cse_semester"] <= 8, (
            f"cse_semester out of range 1-8 in {code}: {course['cse_semester']}"
        )

        # 6. skills is a non-empty list of strings
        assert isinstance(course["skills"], list) and len(course["skills"]) > 0, (
            f"skills must be a non-empty list in {code}"
        )
        assert all(isinstance(s, str) and len(s.strip()) > 0 for s in course["skills"]), (
            f"skills must be non-empty strings in {code}"
        )

        # 7. source starts with https://academics.iitp.ac.in/
        assert isinstance(course["source"], str) and course["source"].startswith(
            "https://academics.iitp.ac.in/"
        ), f"source must start with https://academics.iitp.ac.in/ in {code}"
