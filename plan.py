import checker


def build_plan(kb, targets, profile):
    depth_levels = targets.get("depth_levels", ["none", "basic", "course", "interview"])
    depth_index = {d: i for i, d in enumerate(depth_levels)}
    target_list = targets.get("targets", [])
    facts = profile.get("facts", [])

    constants = targets.get("constants", {})
    cap = constants.get("weekly_study_cap_hours", 0)
    horizon = constants.get("horizon_weeks", 0)
    budget = cap * horizon

    skipped = []
    gaps = {}

    # Rule 1, 2, 3: Skip check and depth gap calculation
    for target in target_list:
        tid = target["id"]
        facts_for_topic = [f for f in facts if f.get("topic") == tid]

        if checker.should_skip(target, facts_for_topic, depth_levels=depth_levels):
            skipped.append(tid)
        else:
            if facts_for_topic:
                max_depth_idx = max(depth_index.get(f.get("depth"), 0) for f in facts_for_topic)
            else:
                max_depth_idx = depth_index.get("none", 0)

            req_depth_idx = depth_index.get(target.get("required_depth"), 0)
            gaps[tid] = req_depth_idx - max_depth_idx

    items = []
    placed_ids = []
    deferred = []
    running_hours = 0

    # Rule 4 & 5: Deterministic ordering and budget enforcement
    while True:
        candidates = []
        for idx, target in enumerate(target_list):
            tid = target["id"]
            if tid in placed_ids or tid in skipped or tid in deferred:
                continue

            order_after = target.get("order_after", [])

            # A target that depends on a deferred target is deferred too
            if any(dep in deferred for dep in order_after):
                deferred.append(tid)
                continue

            # Eligible if all order_after ids are already placed or skipped
            if all(dep in placed_ids or dep in skipped for dep in order_after):
                candidates.append((target, idx))

        if not candidates:
            break

        # Pick target with largest gap; tie-break by position in targets.json
        candidates.sort(key=lambda item: (-gaps[item[0]["id"]], item[1]))
        chosen_target, _ = candidates[0]
        chosen_id = chosen_target["id"]
        est_hours = chosen_target.get("est_hours", 0)

        if running_hours + est_hours <= budget:
            placed_ids.append(chosen_id)
            items.append({"target_id": chosen_id, "order": len(items) + 1})
            running_hours += est_hours
        else:
            deferred.append(chosen_id)

    # Any remaining non-placed, non-skipped targets are deferred
    for target in target_list:
        tid = target["id"]
        if tid not in placed_ids and tid not in skipped and tid not in deferred:
            deferred.append(tid)

    return {
        "items": items,
        "skipped": skipped,
        "deferred": deferred,
    }
