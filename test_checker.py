import copy
import pytest

import checker


def get_good_plan():
    return {
        "items": [
            {"target_id": "dsa.core", "order": 1},
            {"target_id": "dsa.dp", "order": 2},
            {"target_id": "dsa.greedy_backtracking", "order": 3},
            {"target_id": "os.core", "order": 4},
            {"target_id": "dbms.core", "order": 5},
            {"target_id": "cn.core", "order": 6},
            {"target_id": "proj.web_backend", "order": 7},
        ],
        "skipped": ["dsa.graphs"],
    }


def test_good_plan_passes():
    kb, targets, profile = checker.load_data()
    plan = get_good_plan()
    violations = checker.check_plan(plan, kb, targets, profile)
    assert violations == []


def test_fake_target_id_fails():
    kb, targets, profile = checker.load_data()
    plan = get_good_plan()
    plan["items"].append({"target_id": "nonexistent.target", "order": 8})
    violations = checker.check_plan(plan, kb, targets, profile)
    assert any("nonexistent.target" in v for v in violations)


def test_duplicate_item_fails():
    kb, targets, profile = checker.load_data()
    plan = get_good_plan()
    plan["items"].append({"target_id": "os.core", "order": 8})
    violations = checker.check_plan(plan, kb, targets, profile)
    assert any("duplicate" in v.lower() and "os.core" in v for v in violations)


def test_target_both_in_items_and_skipped_fails():
    kb, targets, profile = checker.load_data()
    plan = get_good_plan()
    plan["skipped"].append("os.core")
    violations = checker.check_plan(plan, kb, targets, profile)
    assert any("os.core" in v for v in violations)


def test_skipping_dsa_dp_fails():
    kb, targets, profile = checker.load_data()
    plan = get_good_plan()
    plan["items"] = [item for item in plan["items"] if item["target_id"] != "dsa.dp"]
    plan["skipped"].append("dsa.dp")
    violations = checker.check_plan(plan, kb, targets, profile)
    assert any("dsa.dp" in v for v in violations)


def test_skipping_dbms_core_fails():
    kb, targets, profile = checker.load_data()
    plan = get_good_plan()
    plan["items"] = [item for item in plan["items"] if item["target_id"] != "dbms.core"]
    plan["skipped"].append("dbms.core")
    violations = checker.check_plan(plan, kb, targets, profile)
    assert any("dbms.core" in v for v in violations)


def test_skipping_dsa_core_fails():
    kb, targets, profile = checker.load_data()
    plan = get_good_plan()
    plan["items"] = [item for item in plan["items"] if item["target_id"] != "dsa.core"]
    plan["skipped"].append("dsa.core")
    violations = checker.check_plan(plan, kb, targets, profile)
    assert any("dsa.core" in v for v in violations)


def test_ordering_dsa_dp_before_dsa_core_fails():
    kb, targets, profile = checker.load_data()
    plan = {
        "items": [
            {"target_id": "dsa.dp", "order": 1},
            {"target_id": "dsa.core", "order": 2},
            {"target_id": "dsa.greedy_backtracking", "order": 3},
            {"target_id": "os.core", "order": 4},
            {"target_id": "dbms.core", "order": 5},
            {"target_id": "cn.core", "order": 6},
            {"target_id": "proj.web_backend", "order": 7},
        ],
        "skipped": ["dsa.graphs"],
    }
    violations = checker.check_plan(plan, kb, targets, profile)
    assert any("dsa.core" in v and "dsa.dp" in v for v in violations)


def test_budget_exceeded_fails():
    kb, targets, profile = checker.load_data()
    # Pass a deep copy of targets, never editing the file
    targets_mod = copy.deepcopy(targets)
    for t in targets_mod["targets"]:
        if t["id"] == "dsa.core":
            t["est_hours"] = 200

    plan = get_good_plan()
    violations = checker.check_plan(plan, kb, targets_mod, profile)
    assert any("budget" in v.lower() for v in violations)


def test_unknown_defined_by_fails():
    kb, targets, profile = checker.load_data()
    # Pass a deep copy of targets, never editing the file
    targets_mod = copy.deepcopy(targets)
    for t in targets_mod["targets"]:
        if t["id"] == "dsa.core":
            t["defined_by"] = "CS9999"

    plan = get_good_plan()
    violations = checker.check_plan(plan, kb, targets_mod, profile)
    assert any("CS9999" in v for v in violations)


def test_should_skip_depth_and_trust():
    target = {"id": "topic.test", "required_depth": "interview"}

    # graded-only course-depth fact does not clear an interview target
    facts_course_depth = [
        {"topic": "topic.test", "depth": "course", "source": "graded", "trust": "high", "claim": "", "evidence": ""}
    ]
    assert checker.should_skip(target, facts_course_depth) is False

    # tested interview medium fact clears an interview target
    facts_tested_interview = [
        {"topic": "topic.test", "depth": "interview", "source": "tested", "trust": "medium", "claim": "", "evidence": ""}
    ]
    assert checker.should_skip(target, facts_tested_interview) is True

    # self-declared fact never clears
    facts_self_declared = [
        {"topic": "topic.test", "depth": "interview", "source": "self_declared", "trust": "medium", "claim": "", "evidence": ""}
    ]
    assert checker.should_skip(target, facts_self_declared) is False


def test_course_credits():
    # Test with string course code
    credits_code = checker.course_credits("CS1101")
    assert credits_code == 4.5

    # Test with course dict (never trusts stored total, computes from ltpc)
    course_dict = {"code": "CS1101", "ltpc": "3-0-3-4.5", "credits": 999.0}
    assert checker.course_credits(course_dict) == 4.5
