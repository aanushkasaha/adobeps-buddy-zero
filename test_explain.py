import copy
import pytest

import checker
import plan
import llm
import explain


def test_good_json_reply_uses_llm_source(monkeypatch):
    kb, targets, profile = checker.load_data()
    p = plan.build_plan(kb, targets, profile)

    def mock_call_llm(messages, expect_json=False):
        return {"why": "Mastering this target is critical for interview preparation."}

    monkeypatch.setattr(llm, "call_llm", mock_call_llm)

    res = explain.explain_plan(p, kb, targets, profile)
    assert len(res) == len(p["items"]) + len(p["skipped"]) + len(p["deferred"])

    for entry in res:
        if entry["status"] == "item":
            assert entry["source"] == "llm"
            assert entry["why"] == "Mastering this target is critical for interview preparation."
        elif entry["status"] == "skipped":
            assert entry["source"] == "template"
            assert "F3" in entry["why"]  # F3 cleared dsa.graphs


def test_call_llm_raises_runtime_error_falls_back(monkeypatch):
    kb, targets, profile = checker.load_data()
    p = plan.build_plan(kb, targets, profile)

    def mock_call_llm(messages, expect_json=False):
        raise RuntimeError("LLM rate limit reached; failed after 3 retries.")

    monkeypatch.setattr(llm, "call_llm", mock_call_llm)

    res = explain.explain_plan(p, kb, targets, profile)
    for entry in res:
        if entry["status"] == "item":
            assert entry["source"] == "template"
            assert isinstance(entry["why"], str) and len(entry["why"].strip()) > 0


def test_call_llm_raises_value_error_falls_back(monkeypatch):
    kb, targets, profile = checker.load_data()
    p = plan.build_plan(kb, targets, profile)

    def mock_call_llm(messages, expect_json=False):
        raise ValueError("Failed to parse valid JSON from LLM response after retry.")

    monkeypatch.setattr(llm, "call_llm", mock_call_llm)

    res = explain.explain_plan(p, kb, targets, profile)
    for entry in res:
        if entry["status"] == "item":
            assert entry["source"] == "template"
            assert isinstance(entry["why"], str) and len(entry["why"].strip()) > 0


def test_call_llm_raises_connection_error_falls_back(monkeypatch):
    kb, targets, profile = checker.load_data()
    p = plan.build_plan(kb, targets, profile)

    def mock_call_llm(messages, expect_json=False):
        raise ConnectionError("Connection refused by host.")

    monkeypatch.setattr(llm, "call_llm", mock_call_llm)

    res = explain.explain_plan(p, kb, targets, profile)
    for entry in res:
        if entry["status"] == "item":
            assert entry["source"] == "template"
            assert isinstance(entry["why"], str) and len(entry["why"].strip()) > 0


def test_reply_is_list_falls_back(monkeypatch):
    kb, targets, profile = checker.load_data()
    p = plan.build_plan(kb, targets, profile)

    def mock_call_llm(messages, expect_json=False):
        return [{"why": "A list instead of a dict."}]

    monkeypatch.setattr(llm, "call_llm", mock_call_llm)

    res = explain.explain_plan(p, kb, targets, profile)
    for entry in res:
        if entry["status"] == "item":
            assert entry["source"] == "template"
            assert isinstance(entry["why"], str) and len(entry["why"].strip()) > 0


def test_reply_missing_or_empty_why_falls_back(monkeypatch):
    kb, targets, profile = checker.load_data()
    p = plan.build_plan(kb, targets, profile)

    responses = [{"other": "value"}, {"why": ""}, {"why": 12345}, {"why": "   "}]
    idx = 0

    def mock_call_llm(messages, expect_json=False):
        nonlocal idx
        resp = responses[idx % len(responses)]
        idx += 1
        return resp

    monkeypatch.setattr(llm, "call_llm", mock_call_llm)

    res = explain.explain_plan(p, kb, targets, profile)
    for entry in res:
        if entry["status"] == "item":
            assert entry["source"] == "template"
            assert isinstance(entry["why"], str) and len(entry["why"].strip()) > 0


def test_call_count_one_per_item_zero_for_skipped_deferred(monkeypatch):
    kb, targets, profile = checker.load_data()
    targets_mod = copy.deepcopy(targets)
    targets_mod["constants"]["horizon_weeks"] = 1  # forces some items to be deferred
    p = plan.build_plan(kb, targets_mod, profile)

    assert len(p["items"]) > 0
    assert len(p["skipped"]) > 0
    assert len(p["deferred"]) > 0

    call_count = 0

    def mock_call_llm(messages, expect_json=False):
        nonlocal call_count
        call_count += 1
        return {"why": "Detailed item explanation."}

    monkeypatch.setattr(llm, "call_llm", mock_call_llm)

    res = explain.explain_plan(p, kb, targets_mod, profile)

    # Exactly 1 call per item, zero for skipped and deferred
    assert call_count == len(p["items"])

    statuses = {entry["target_id"]: entry["status"] for entry in res}
    for item in p["items"]:
        assert statuses[item["target_id"]] == "item"
    for sid in p["skipped"]:
        assert statuses[sid] == "skipped"
    for did in p["deferred"]:
        assert statuses[did] == "deferred"


def test_prompt_isolation_no_other_target_data(monkeypatch):
    kb, targets, profile = checker.load_data()
    p = plan.build_plan(kb, targets, profile)

    all_target_ids = {t["id"] for t in targets["targets"]}
    all_facts = profile["facts"]

    prompts_by_target = {}

    def mock_call_llm(messages, expect_json=False):
        content = " ".join(m.get("content", "") for m in messages)
        # determine which target this prompt is for
        current_target = None
        for tid in all_target_ids:
            if tid in content:
                current_target = tid
                break
        prompts_by_target[current_target] = content
        return {"why": "Target explanation."}

    monkeypatch.setattr(llm, "call_llm", mock_call_llm)

    _ = explain.explain_plan(p, kb, targets, profile)

    for item in p["items"]:
        tid = item["target_id"]
        assert tid in prompts_by_target, f"No prompt captured for {tid}"
        prompt_text = prompts_by_target[tid]

        # Other targets and their specific fact IDs must not appear in prompt_text
        for other_t in targets["targets"]:
            other_id = other_t["id"]
            if other_id == tid:
                continue

            # Ensure other target's fact IDs do not appear
            other_facts = [f for f in all_facts if f.get("topic") == other_id]
            for f in other_facts:
                assert f["id"] not in prompt_text, (
                    f"Prompt for {tid} leaked fact ID {f['id']} of target {other_id}"
                )


def test_plan_passed_in_is_not_mutated(monkeypatch):
    kb, targets, profile = checker.load_data()
    p = plan.build_plan(kb, targets, profile)
    p_copy = copy.deepcopy(p)

    def mock_call_llm(messages, expect_json=False):
        return {"why": "Explanation text."}

    monkeypatch.setattr(llm, "call_llm", mock_call_llm)

    _ = explain.explain_plan(p, kb, targets, profile)

    assert p == p_copy
