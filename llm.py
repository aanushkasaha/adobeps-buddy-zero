import json
import os
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from litellm import completion, RateLimitError, Timeout

# Load environment variables without exposing sensitive values
load_dotenv()


# Append token usage metadata to log file after each successful call
def _log_usage(usage):
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
    }
    with open("llm_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")


# Send request with retry logic for rate limits, timeouts, and empty replies
def _send_request(messages):
    rate_retries = 0
    timeout_retries = 0
    empty_retries = 0
    delays = [2, 4, 8]

    while True:
        try:
            r = completion(
                model=os.environ["LLM_MODEL"],
                api_key=os.environ["LLM_API_KEY"],
                messages=messages,
                temperature=0,
                timeout=30,
            )
            _log_usage(r.usage)
            content = r.choices[0].message.content
            if not content or not content.strip():
                if empty_retries < 1:
                    empty_retries += 1
                    continue
                raise ValueError("LLM returned an empty response after retry.")
            return content
        except RateLimitError as e:
            if rate_retries < len(delays):
                time.sleep(delays[rate_retries])
                rate_retries += 1
                continue
            raise RuntimeError("LLM rate limit reached; failed after 3 retries.") from e
        except Timeout as e:
            if timeout_retries < 1:
                timeout_retries += 1
                continue
            raise RuntimeError("LLM request timed out after retry.") from e


# Call LLM and optionally parse and validate JSON response
def call_llm(messages, expect_json=False):
    reply = _send_request(messages)
    if not expect_json:
        return reply

    try:
        return json.loads(reply)
    except json.JSONDecodeError:
        followup = list(messages) + [
            {"role": "assistant", "content": reply},
            {"role": "user", "content": "The previous reply was not valid JSON. Please reply with valid JSON only."},
        ]
        retry_reply = _send_request(followup)
        try:
            return json.loads(retry_reply)
        except json.JSONDecodeError as err:
            raise ValueError("Failed to parse valid JSON from LLM response after retry.") from err
