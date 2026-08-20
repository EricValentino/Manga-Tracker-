import os 
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_recommendations(manga_list):
    manga_summary = "\n".join(
        f"- {m.title} ({m.genre})" for m in manga_list 
    )

    prompt = f"""Here is a user's manga reading list: 
{manga_summary}

recommend 4 manga they have not already read that they would likely enjoy.
respond ONLY with raw JSON in this exact shape, no other text: 
{{"recommendations": [{{"title": "string", "genre": "string", "reason": "one sentence why they'd like it"}}]}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    raw_text = response.choices[0].message.content
    data = json.loads(raw_text)
    return data["recommendations"]