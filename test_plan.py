import copy
import pytest

import checker
import plan


def test_real_data_plan_passes_checker():
    kb, targets, profile = checker.load_data()
    p = plan.build_plan(kb, targets, profile)
    violations = checker.check_plan(p, kb, targets, profile)
    assert violations == []


def test_dsa_graphs_skipped_and_others_items():
    kb, targets, profile = checker.load_data()
    p = plan.build_plan(kb, targets, profile)
    assert p["skipped"] == ["dsa.graphs"]

    item_ids = [item["target_id"] for item in p["items"]]
    assert len(item_ids) == 7
    assert "dsa.graphs" not in item_ids
    assert set(item_ids) == {
        "dsa.core",
        "dsa.dp",
        "dsa.greedy_backtracking",
        "os.core",
        "dbms.core",
        "cn.core",
        "proj.web_backend",
    }


def test_prerequisite_ordering():
    kb, targets, profile = checker.load_data()
    p = plan.build_plan(kb, targets, profile)
    item_ids = [item["target_id"] for item in p["items"]]

    core_idx = item_ids.index("dsa.core")
    dp_idx = item_ids.index("dsa.dp")
    greedy_idx = item_ids.index("dsa.greedy_backtracking")

    assert core_idx < dp_idx
    assert core_idx < greedy_idx


def test_deterministic_output():
    kb, targets, profile = checker.load_data()
    plan1 = plan.build_plan(kb, targets, profile)
    plan2 = plan.build_plan(kb, targets, profile)
    assert plan1 == plan2


def test_fact_f3_removed_unskips_dsa_graphs():
    kb, targets, profile = checker.load_data()
    profile_mod = copy.deepcopy(profile)
    profile_mod["facts"] = [f for f in profile_mod["facts"] if f["id"] != "F3"]

    p = plan.build_plan(kb, targets, profile_mod)
    item_ids = [item["target_id"] for item in p["items"]]

    assert "dsa.graphs" in item_ids
    assert "dsa.graphs" not in p["skipped"]


def test_budget_tiny_horizon_weeks_defers():
    kb, targets, profile = checker.load_data()
    targets_mod = copy.deepcopy(targets)
    targets_mod["constants"]["horizon_weeks"] = 1  # Cap is 12 * 1 = 12 hours

    # Rider 2: Pass the same modified copy of targets to both build_plan and check_plan
    p = plan.build_plan(kb, targets_mod, profile)

    assert len(p["deferred"]) > 0

    violations = checker.check_plan(p, kb, targets_mod, profile)
    assert violations == []

    # Verify running sum of est_hours never exceeds budget
    budget = targets_mod["constants"]["weekly_study_cap_hours"] * targets_mod["constants"]["horizon_weeks"]
    target_map = {t["id"]: t for t in targets_mod["targets"]}
    total_hours = sum(target_map[it["target_id"]]["est_hours"] for it in p["items"])
    assert total_hours <= budget


def test_build_plan_never_mutates_inputs():
    kb, targets, profile = checker.load_data()
    kb_copy = copy.deepcopy(kb)
    targets_copy = copy.deepcopy(targets)
    profile_copy = copy.deepcopy(profile)

    _ = plan.build_plan(kb, targets, profile)

    assert kb == kb_copy
    assert targets == targets_copy
    assert profile == profile_copy
