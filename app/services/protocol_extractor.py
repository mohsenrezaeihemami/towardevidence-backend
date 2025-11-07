import fitz
import openai
import json
from app.core.config import settings

openai.api_key = settings.OPENAI_API_KEY

SYSTEM_PROMPT = "You are a professional systematic reviewer. Extract structured inclusion/exclusion config from a protocol. Return ONLY valid JSON."

SCHEMA_HINT = '''
{
  "year_window": {
    "enabled": bool,
    "min": int or null,
    "max": int or null,
    "required_for_decision": bool
  },
  "language": {
    "enabled": bool,
    "allow": [string],
    "required_for_decision": bool
  },
  "population": {
    "free_text": string,
    "include_keywords": [string],
    "exclude_keywords": [string]
  },
  "interventions": {
    "free_text": string,
    "include_keywords": [string],
    "exclude_keywords": [string]
  },
  "comparators": {
    "free_text": string
  },
  "outcomes": {
    "enabled": bool,
    "required_topics": [string]
  },
  "study_design": {
    "enabled": bool,
    "include": [string],
    "exclude": [string]
  },
  "sample_size": {
    "enabled": bool,
    "min": int or null,
    "required_for_exclusion": bool
  },
  "followup": {
    "enabled": bool,
    "min_months": int or null
  },
  "keyword_exclusions": {
    "enabled": bool,
    "terms": [string]
  }
}
'''

def _extract_text_from_pdf(path: str, max_chars: int = 12000) -> str:
    doc = fitz.open(path)
    texts = []
    total = 0
    for page in doc:
        t = page.get_text("text")
        if not t:
            continue
        if total + len(t) > max_chars:
            t = t[: max_chars - total]
            texts.append(t)
            break
        texts.append(t)
        total += len(t)
    return "\n".join(texts)

def extract_protocol_config(path: str) -> dict:
    if not settings.OPENAI_API_KEY:
        return {}

    text = _extract_text_from_pdf(path)
    user_prompt = f"Protocol text:\n{text}\n\nSchema:\n{SCHEMA_HINT}\n\nReturn ONLY JSON."
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        temperature=0.1,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = resp.choices[0].message["content"]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}
    return data
