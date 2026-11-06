# Buddy Zero

## What It Is
A study buddy for one fictional student (non-CS, Chemical and Biochemical Engineering, IIT Patna) aiming for software roles. Track: Personalisation.

## How to Run
- Activate environment: `source .venv/bin/activate`
- Run pipeline: `python main.py`
- Run tests: `python -m pytest -q`
- Setup: Requires a `.env` file containing `LLM_MODEL` and `LLM_API_KEY` (never include a real value).

## Files
- `kb.json`: IIT Patna course curriculum (7 courses) and academic rules data.
- `targets.json`: Software interview targets, depth levels, estimated hours, dependencies, and constants.
- `profile.json`: Fictional student profile with graded, tested, and self-declared background facts.
- `checker.py`: Pure-code verification of plan validity, credits formula (L+T+P/2), prerequisites, and budget.
- `plan.py`: Deterministic planner selecting targets by largest depth gap within study hour limits.
- `explain.py`: Generates item explanations via LLM with automatic template fallback for skipped/deferred items and errors.
- `llm.py`: LiteLLM wrapper with rate limit/timeout retries, JSON validation, and token logging.
- `main.py`: CLI entry point running load, plan, check, explain, and printing/saving output.
- `last_plan.json`: Output file persisting the most recently generated study plan and explanations.
- `llm_log.jsonl`: Append-only log recording timestamp and token usage for successful LLM requests.

## LLM vs Code
- The LLM only writes the "why" text per plan item.
- Rule checks, credit maths, skip decisions, ordering, and budget are strictly code.
- If `check_plan` finds a violation, `main.py` stops before any LLM call.
- If an LLM call fails, a template explanation is used automatically.

## Known Gaps
- Rules R1–R3 in `kb.json` are student-reported with no official link.
- CS3101, CS3102, and CS2202 entries are not yet verified against the IITP page.
- `kb.json` has 7 courses.
- `llm.py` does not retry connection or 5xx errors and does not handle JSON in markdown fences.
- `temperature=0` does not guarantee identical LLM text, so plan determinism comes from the code.
- All profile data is fictional.
