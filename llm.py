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


# Send request with timeout and rate-limit retry logic
def _send_request(messages):
    rate_retries = 0
    timeout_retries = 0
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
            return r.choices[0].message.content
        except (RateLimitError, Exception) as e:
            if isinstance(e, RateLimitError) or getattr(e, "status_code", None) == 429:
                if rate_retries < len(delays):
                    time.sleep(delays[rate_retries])
                    rate_retries += 1
                    continue
                raise RuntimeError("LLM rate limit reached; failed after 3 retries.") from e
            if isinstance(e, (Timeout, TimeoutError)):
                if timeout_retries < 1:
                    timeout_retries += 1
                    continue
                raise RuntimeError("LLM request timed out after retry.") from e
            raise


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
