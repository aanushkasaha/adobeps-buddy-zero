import os
from dotenv import load_dotenv
from litellm import completion

load_dotenv()
r = completion(
    model=os.environ["LLM_MODEL"],
    api_key=os.environ["LLM_API_KEY"],
    messages=[{"role": "user", "content": "Say hi"}],
)
print(r.choices[0].message.content)
