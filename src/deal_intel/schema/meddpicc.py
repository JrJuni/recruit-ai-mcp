from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MeddpiccField(BaseModel):
    score: int = Field(default=0, ge=0, le=5)
    evidence: str = ""


class Meddpicc(BaseModel):
    metrics: Optional[MeddpiccField] = None
    economic_buyer: Optional[MeddpiccField] = None
    decision_criteria: Optional[MeddpiccField] = None
    decision_process: Optional[MeddpiccField] = None
    identify_pain: Optional[MeddpiccField] = None
    champion: Optional[MeddpiccField] = None
    competition: Optional[MeddpiccField] = None

    def total_score(self) -> int:
        fields = [
            self.metrics, self.economic_buyer, self.decision_criteria,
            self.decision_process, self.identify_pain, self.champion, self.competition,
        ]
        return sum(f.score for f in fields if f is not None)

    def filled_count(self) -> int:
        fields = [
            self.metrics, self.economic_buyer, self.decision_criteria,
            self.decision_process, self.identify_pain, self.champion, self.competition,
        ]
        return sum(1 for f in fields if f is not None)


class Meeting(BaseModel):
    meeting_id: str
    date: str
    raw_notes: str
    summary: str = ""
    meddpicc: Optional[dict] = None  # raw dict from LLM, validated on read


class Deal(BaseModel):
    deal_id: str
    company: str
    industry: Optional[str] = None
    deal_size_krw: Optional[int] = None
    contacts: list[str] = Field(default_factory=list)
    meetings: list[dict] = Field(default_factory=list)
    deal_stage: str = "discovery"
    close_reason: Optional[str] = None
    bd_strategy: str = ""
    gtm_notes: str = ""
    prospect_id: Optional[str] = None  # link to event-intel-mcp prospect
    created_at: str = ""
    updated_at: str = ""
