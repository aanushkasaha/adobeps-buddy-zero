# Buddy Zero

## What It Is

A study buddy for one fictional student (non-CS, Chemical and Biochemical Engineering, IIT Patna) aiming for software roles. Track: Personalisation.

## How to Run

* Activate environment: `source .venv/bin/activate`
* Run pipeline: `python main.py`
* Run tests: `python -m pytest -q`
* Setup: requires a `.env` file containing `LLM_MODEL` and `LLM_API_KEY` (never commit a real value).

## Files

* `kb.json`: IIT Patna course curriculum (7 courses) and academic rules (R1 to R3), compiled and checked by the author (see Data Provenance).
* `targets.json`: software interview targets, depth levels, estimated hours, dependencies and constants.
* `profile.json`: fictional student profile with graded, tested and self-declared background facts.
* `checker.py`: pure-code verification of plan validity, the credits formula (L + T + P/2), prerequisites and the study-hour budget.
* `plan.py`: deterministic planner that selects targets by largest depth gap within the study-hour limit.
* `explain.py`: generates item explanations via the LLM, with an automatic template fallback for skipped or deferred items and on errors.
* `llm.py`: LiteLLM wrapper with rate-limit and timeout retries, JSON validation and token logging.
* `main.py`: CLI entry point that loads data, plans, checks, explains, then prints and saves the output.
* `last_plan.json`: the most recently generated study plan and explanations.
* `llm_log.jsonl`: append-only log of timestamp and token usage for each successful LLM request.

## LLM vs Code

* The LLM only writes the "why" text for each plan item.
* Rule checks, credit maths, skip decisions, ordering and the budget are strictly code.
* If `check_plan` finds a violation, `main.py` stops before any LLM call.
* If an LLM call fails, a template explanation is used automatically.

## Results (live run, nvidia/nemotron-3.5-lightning:free)

- Plan: 7 items, 115 h of a 120 h budget (12 h/week x 10 weeks); 1 target skipped because a tested profile fact already shows interview-level depth
- LLM usage: 7 calls, 5,984 tokens total (974 prompt / 5,010 completion), about 854 per call
- End-to-end time: about 40 s (about 4 s CPU; the rest is waiting on the free endpoint)
- Cost: $0
- Completion tokens dominate because the model is a reasoning model
- Single run; token counts vary between runs

## Data Provenance

* `kb.json` (7 courses and rules R1 to R3) was compiled and cross-checked by the author, a current IIT Patna student, against the course structure and academic rules as they apply at the institute.
* Public source links are not attached to the rules or to the CS3101, CS3102 and CS2202 entries yet. Adding them is the next step.
* All profile data is fictional.

## Known Gaps

* `llm.py` does not retry connection or 5xx errors and does not handle JSON wrapped in markdown fences.
* `temperature=0` does not guarantee identical LLM text, so plan determinism comes from the code, not the model.
* The knowledge base is small (7 courses), so plans cover a limited set of targets.
