import json
import pytest


def load_targets_data():
    with open("targets.json", "r", encoding="utf-8") as f:
        return json.load(f)


def test_target_est_hours():
    data = load_targets_data()
    targets = data["targets"]
    assert len(targets) > 0, "targets list is empty"

    for target in targets:
        # Direct key access so missing field fails loudly with KeyError
        est = target["est_hours"]
        assert type(est) is int, f"Target {target.get('id')} est_hours is not an int: {type(est)}"
        assert est > 0, f"Target {target.get('id')} est_hours must be > 0: {est}"


def test_target_order_after_valid_references():
    data = load_targets_data()
    targets = data["targets"]
    target_ids = {t["id"] for t in targets}

    for target in targets:
        tid = target["id"]
        # Direct key access
        order_after = target["order_after"]
        assert isinstance(order_after, list), f"Target {tid} order_after is not a list"

        for dep in order_after:
            assert dep != tid, f"Target {tid} references itself in order_after"
            assert dep in target_ids, f"Target {tid} references unknown target '{dep}' in order_after"


def test_target_order_after_acyclic():
    data = load_targets_data()
    targets = data["targets"]

    # Direct key access to build graph
    graph = {t["id"]: t["order_after"] for t in targets}

    # DFS cycle detection: 0 = unvisited, 1 = visiting, 2 = visited
    state = {}

    def has_cycle(node):
        state[node] = 1
        for neighbor in graph.get(node, []):
            if state.get(neighbor) == 1:
                return True
            if state.get(neighbor) != 2:
                if has_cycle(neighbor):
                    return True
        state[node] = 2
        return False

    for node in graph:
        if state.get(node) != 2:
            assert not has_cycle(node), f"Cycle detected in order_after involving target '{node}'"


def test_targets_constants():
    data = load_targets_data()
    # Direct key access
    constants = data["constants"]

    cap = constants["weekly_study_cap_hours"]
    horizon = constants["horizon_weeks"]

    assert type(cap) is int and cap > 0, f"weekly_study_cap_hours must be int > 0, got {cap}"
    assert type(horizon) is int and horizon > 0, f"horizon_weeks must be int > 0, got {horizon}"
