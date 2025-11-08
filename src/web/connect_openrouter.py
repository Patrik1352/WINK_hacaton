from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv('../../.env')
LLM_API_KEY = os.environ['LLM_API_KEY']
if not LLM_API_KEY:
    raise ValueError("LLM_API_KEY не найден в .env файле")


client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=LLM_API_KEY,
)

def get_response_llm(query = 'What is the meaning of life?', model = 'mistralai/mistral-7b-instruct:free'):
    completion = client.chat.completions.create(
      # extra_headers={
      #   "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
      #   "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
      # },
      extra_body={},
      model=model,
      messages=[
                  {
                    "role": "user",
                    "content": query
                  }
                ]
    )
    return completion.choices[0].message.content