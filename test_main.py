import json
import shutil
from pathlib import Path
import pytest

import checker
import llm
import main


@pytest.fixture
def setup_tmp_workspace(tmp_path, monkeypatch):
    # Copy the three json files to tmp_path so checker.load_data works relative to cwd
    repo_root = Path(__file__).resolve().parent
    for filename in ["kb.json", "targets.json", "profile.json"]:
        shutil.copy(repo_root / filename, tmp_path / filename)

    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_main_success_real_data(setup_tmp_workspace, monkeypatch):
    def mock_call_llm(messages, expect_json=False):
        return {"why": "Mastering this target is critical for interview preparation."}

    monkeypatch.setattr(llm, "call_llm", mock_call_llm)

    exit_code = main.main()
    assert exit_code == 0

    # Verify last_plan.json was written to tmp_path
    last_plan_file = setup_tmp_workspace / "last_plan.json"
    assert last_plan_file.exists()

    with open(last_plan_file, "r", encoding="utf-8") as f:
        saved_data = json.load(f)

    assert "plan" in saved_data
    assert "explanations" in saved_data
    assert len(saved_data["plan"]["items"]) == 7


def test_main_runtime_error_fallback(setup_tmp_workspace, monkeypatch):
    def mock_call_llm(messages, expect_json=False):
        raise RuntimeError("LLM rate limit reached; failed after 3 retries.")

    monkeypatch.setattr(llm, "call_llm", mock_call_llm)

    exit_code = main.main()
    assert exit_code == 0

    last_plan_file = setup_tmp_workspace / "last_plan.json"
    assert last_plan_file.exists()


def test_main_check_plan_violation_exits_1_no_llm(setup_tmp_workspace, monkeypatch, capsys):
    llm_called = False

    def mock_call_llm(messages, expect_json=False):
        nonlocal llm_called
        llm_called = True
        return {"why": "Explanation"}

    def mock_check_plan(plan_dict, kb, targets, profile):
        return ["Simulated test violation: target budget exceeded."]

    monkeypatch.setattr(llm, "call_llm", mock_call_llm)
    monkeypatch.setattr(checker, "check_plan", mock_check_plan)

    exit_code = main.main()
    assert exit_code == 1
    assert llm_called is False

    # Rider 2: Violations printed to stdout
    captured = capsys.readouterr()
    assert "Simulated test violation: target budget exceeded." in captured.out


def test_main_last_plan_written_to_tmp_path_only(setup_tmp_workspace, monkeypatch):
    def mock_call_llm(messages, expect_json=False):
        return {"why": "Sample reason"}

    monkeypatch.setattr(llm, "call_llm", mock_call_llm)

    exit_code = main.main()
    assert exit_code == 0

    # Ensure last_plan.json is in tmp_path
    assert (setup_tmp_workspace / "last_plan.json").is_file()

    # Ensure last_plan.json was NOT written to repo root
    repo_root = Path(__file__).resolve().parent
    repo_last_plan = repo_root / "last_plan.json"
    assert not repo_last_plan.exists()


def test_main_output_contains_every_item_target_id(setup_tmp_workspace, monkeypatch, capsys):
    def mock_call_llm(messages, expect_json=False):
        return {"why": "Study explanation."}

    monkeypatch.setattr(llm, "call_llm", mock_call_llm)

    exit_code = main.main()
    assert exit_code == 0

    captured = capsys.readouterr().out

    # Load targets to check all placed item IDs are in output
    with open("targets.json", "r", encoding="utf-8") as f:
        targets_data = json.load(f)

    # In real data, 7 targets are placed as items
    expected_item_ids = [
        "dsa.core",
        "dsa.dp",
        "dsa.greedy_backtracking",
        "os.core",
        "dbms.core",
        "cn.core",
        "proj.web_backend",
    ]
    for tid in expected_item_ids:
        assert tid in captured, f"Target ID '{tid}' missing from printed stdout"
