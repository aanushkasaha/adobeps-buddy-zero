from unittest.mock import patch, MagicMock
import llm


def fake_reply(content):
    fake = MagicMock()
    fake.choices[0].message.content = content
    fake.usage = None
    return fake


def test_empty_reply_expect_json_raises_valueerror():
    with patch("llm.completion", return_value=fake_reply(None)), \
         patch("time.sleep"):
        try:
            llm.call_llm([{"role": "user", "content": "x"}], expect_json=True)
        except ValueError:
            return
        except Exception as e:
            raise AssertionError(f"wrong error: {type(e).__name__}: {e}")
        raise AssertionError("no error raised")


def test_empty_reply_plain_text_raises_valueerror():
    with patch("llm.completion", return_value=fake_reply(None)), \
         patch("time.sleep"):
        try:
            llm.call_llm([{"role": "user", "content": "x"}], expect_json=False)
        except ValueError:
            return
        raise AssertionError("expected ValueError for empty reply")
