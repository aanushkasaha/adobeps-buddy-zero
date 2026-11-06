import json

DEFAULT_DEPTH_LEVELS = ["none", "basic", "course", "interview"]


def load_data():
    with open("kb.json", "r", encoding="utf-8") as f:
        kb = json.load(f)
    with open("targets.json", "r", encoding="utf-8") as f:
        targets = json.load(f)
    with open("profile.json", "r", encoding="utf-8") as f:
        profile = json.load(f)
    return kb, targets, profile


def course_credits(course, kb=None):
    if isinstance(course, str):
        if kb is None:
            kb, _, _ = load_data()
        matching = [c for c in kb.get("courses", []) if c.get("code") == course]
        if not matching:
            raise ValueError(f"Course code '{course}' not found in kb")
        course_obj = matching[0]
    else:
        course_obj = course

    ltpc = course_obj["ltpc"]
    parts = ltpc.split("-")
    l = float(parts[0])
    t = float(parts[1])
    p = float(parts[2])
    return l + t + p / 2.0


def should_skip(target, facts, depth_levels=None):
    if depth_levels is None:
        depth_levels = DEFAULT_DEPTH_LEVELS

    depth_index = {d: i for i, d in enumerate(depth_levels)}
    target_req_depth = target.get("required_depth")
    target_depth_idx = depth_index.get(target_req_depth, -1)
    target_id = target.get("id")

    for fact in facts:
        if fact.get("topic") != target_id:
            continue
        if fact.get("source") not in {"graded", "tested"}:
            continue
        if fact.get("trust") not in {"medium", "high"}:
            continue
        fact_depth = fact.get("depth")
        fact_depth_idx = depth_index.get(fact_depth, -1)
        if fact_depth_idx >= target_depth_idx:
            return True

    return False


def check_plan(plan, kb, targets, profile):
    violations = []
    depth_levels = targets.get("depth_levels", DEFAULT_DEPTH_LEVELS)
    target_map = {t["id"]: t for t in targets.get("targets", [])}
    kb_course_codes = {c["code"] for c in kb.get("courses", [])}
    facts = profile.get("facts", [])

    items = plan.get("items", [])
    skipped = plan.get("skipped", [])

    # 1. Unknown target id (item or skipped)
    for item in items:
        tid = item.get("target_id")
        if tid not in target_map:
            violations.append(f"Unknown target ID in items: '{tid}'")

    for tid in skipped:
        if tid not in target_map:
            violations.append(f"Unknown target ID in skipped: '{tid}'")

    # 2. Course code: a target with defined_by not null must exist in kb courses
    plan_target_ids = set()
    for item in items:
        tid = item.get("target_id")
        if tid in target_map:
            plan_target_ids.add(tid)
    for tid in skipped:
        if tid in target_map:
            plan_target_ids.add(tid)

    for tid in plan_target_ids:
        t = target_map[tid]
        defined_by = t.get("defined_by")
        if defined_by is not None and defined_by not in kb_course_codes:
            violations.append(
                f"Course code '{defined_by}' for target '{tid}' does not exist in kb courses"
            )

    # 3. Duplicate item
    seen_items = set()
    for item in items:
        tid = item.get("target_id")
        if tid in seen_items:
            violations.append(f"Duplicate item found in items: '{tid}'")
        seen_items.add(tid)

    # 4. A target both in items and skipped
    overlap = seen_items.intersection(set(skipped))
    for tid in overlap:
        violations.append(f"Target '{tid}' is present in both items and skipped")

    # 5. Skip not justified (should_skip is False for a skipped target)
    for tid in skipped:
        if tid in target_map:
            t = target_map[tid]
            if not should_skip(t, facts, depth_levels=depth_levels):
                violations.append(f"Skip not justified for target '{tid}'")

    # 6. Ordering: if A is in order_after of B and both are in items, A must come before B
    order_positions = {}
    for idx, item in enumerate(items):
        tid = item.get("target_id")
        if tid not in order_positions:
            order_positions[tid] = item.get("order", idx)

    for item in items:
        b_id = item.get("target_id")
        if b_id in target_map:
            t = target_map[b_id]
            for a_id in t.get("order_after", []):
                if a_id in order_positions:
                    if order_positions[a_id] >= order_positions[b_id]:
                        violations.append(
                            f"Ordering violation: '{a_id}' must come before '{b_id}', but appears at or after it"
                        )

    # 7. Budget: sum of est_hours of items must be <= weekly_study_cap_hours * horizon_weeks
    constants = targets.get("constants", {})
    cap = constants.get("weekly_study_cap_hours", 0)
    horizon = constants.get("horizon_weeks", 0)
    budget = cap * horizon

    total_est_hours = sum(
        target_map[item["target_id"]].get("est_hours", 0)
        for item in items
        if item.get("target_id") in target_map
    )

    if total_est_hours > budget:
        violations.append(
            f"Budget exceeded: total estimated hours {total_est_hours} exceeds budget of {budget} ({cap} * {horizon})"
        )

    return violations
