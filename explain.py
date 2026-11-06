import llm


def explain_plan(plan, kb, targets, profile):
    depth_levels = targets.get("depth_levels", ["none", "basic", "course", "interview"])
    depth_index = {d: i for i, d in enumerate(depth_levels)}
    target_map = {t["id"]: t for t in targets.get("targets", [])}
    course_map = {c["code"]: c for c in kb.get("courses", [])}
    facts = profile.get("facts", [])

    items = plan.get("items", [])
    skipped = plan.get("skipped", [])
    deferred = plan.get("deferred", [])

    results = []

    # 1. Process items (one LLM call per item)
    for item in items:
        tid = item.get("target_id")
        target = target_map.get(tid, {"id": tid, "title": tid, "required_depth": "interview"})

        # Collect facts for this topic in profile order
        facts_for_topic = [f for f in facts if f.get("topic") == tid]

        # Calculate current depth
        if facts_for_topic:
            max_depth_idx = max(depth_index.get(f.get("depth"), 0) for f in facts_for_topic)
            current_depth = depth_levels[max_depth_idx]
        else:
            current_depth = "none"

        # First 1-3 facts in profile order (never from a set)
        selected_facts = facts_for_topic[:3]
        if selected_facts:
            facts_summary = "; ".join(
                f"[{f.get('id')}] claim: {f.get('claim')} (source: {f.get('source')}, trust: {f.get('trust')})"
                for f in selected_facts
            )
        else:
            facts_summary = "None"

        # Course skills from defined_by (none for self_study)
        defined_by = target.get("defined_by")
        if defined_by and defined_by in course_map:
            course_skills = ", ".join(course_map[defined_by].get("skills", []))
        else:
            course_skills = "None (self_study)"

        messages = [
            {
                "role": "user",
                "content": (
                    f"Explain why this target is in the study plan in at most 2 sentences as JSON {{\"why\": \"<max 2 sentences>\"}}.\n"
                    f"Target: {target.get('title')} ({tid})\n"
                    f"Required depth: {target.get('required_depth')}\n"
                    f"Current student depth: {current_depth}\n"
                    f"Student profile facts: {facts_summary}\n"
                    f"Defined course skills: {course_skills}\n"
                ),
            }
        ]

        fallback_why = (
            f"Target '{target.get('title', tid)}' is scheduled to advance depth from {current_depth} "
            f"to {target.get('required_depth')}."
        )

        try:
            resp = llm.call_llm(messages, expect_json=True)
            if (
                isinstance(resp, dict)
                and isinstance(resp.get("why"), str)
                and len(resp["why"].strip()) > 0
            ):
                why_text = resp["why"].strip()
                source_type = "llm"
            else:
                why_text = fallback_why
                source_type = "template"
        except Exception:
            # llm.py lets connection and 5xx errors propagate, and this step must never crash the run.
            why_text = fallback_why
            source_type = "template"

        results.append({
            "target_id": tid,
            "status": "item",
            "why": why_text,
            "source": source_type,
        })

    # 2. Process skipped targets (template in code, no LLM call)
    for sid in skipped:
        target = target_map.get(sid, {"id": sid, "title": sid, "required_depth": "interview"})
        facts_for_topic = [f for f in facts if f.get("topic") == sid]
        target_req_idx = depth_index.get(target.get("required_depth"), 0)

        clearing_fact = None
        for f in facts_for_topic:
            if f.get("source") in {"graded", "tested"} and f.get("trust") in {"medium", "high"}:
                if depth_index.get(f.get("depth"), -1) >= target_req_idx:
                    clearing_fact = f
                    break

        if clearing_fact:
            why_text = (
                f"Skipped because fact {clearing_fact.get('id')} confirms {clearing_fact.get('depth')} depth "
                f"(source: {clearing_fact.get('source')}, trust: {clearing_fact.get('trust')})."
            )
        else:
            why_text = f"Skipped because required depth {target.get('required_depth')} is already satisfied."

        results.append({
            "target_id": sid,
            "status": "skipped",
            "why": why_text,
            "source": "template",
        })

    # 3. Process deferred targets (template in code, no LLM call)
    for did in deferred:
        results.append({
            "target_id": did,
            "status": "deferred",
            "why": "Deferred because the weekly study budget was full.",
            "source": "template",
        })

    return results
