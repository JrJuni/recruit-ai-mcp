from __future__ import annotations

from deal_intel.providers.llm import LLMProvider
from deal_intel.schema.customer_themes import (
    THEME_CATALOG_PROMPT,
    load_json_response,
    normalize_customer_themes,
)

_SYSTEM = "You extract structured customer intelligence from B2B sales meeting notes."

_PROMPT = """\
Extract customer concern themes from the meeting notes.

Only use customer-stated evidence from these MEDDPICC dimensions:
- identify_pain: business problems, severity, urgency
- decision_criteria: selection requirements and evaluation standards
- metrics: measurable outcomes or success criteria

Choose theme_key only from this controlled taxonomy:
{catalog}

For each distinct theme, return:
- theme_key
- dimension
- evidence: direct quote or close paraphrase grounded in the notes
- importance: 1-5, where 5 means explicitly critical or deal-breaking

Return JSON only in this shape:
{{
  "customer_themes": [
    {{"theme_key": "...", "dimension": "...", "evidence": "...", "importance": 1}}
  ]
}}

Return an empty array when there is no grounded evidence. Do not infer unstated concerns.

Meeting notes:
{notes}\
"""


def extract_customer_themes(llm: LLMProvider, raw_notes: str) -> tuple[list[dict], dict]:
    response = llm.chat_once(
        system=_SYSTEM,
        user=_PROMPT.format(catalog=THEME_CATALOG_PROMPT, notes=raw_notes),
        max_tokens=1024,
    )
    payload = load_json_response(response.text)
    raw_themes = payload.get("customer_themes") if isinstance(payload, dict) else []
    return normalize_customer_themes(raw_themes), response.usage
