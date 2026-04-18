"""
Career OS — Pydantic Models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Validation schemas for data flowing between modules.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class JobDescriptionCreate(BaseModel):
    """Input schema for creating a new JD."""
    company: str
    title: str
    location: Optional[str] = None
    location_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    raw_text: str
    source_url: Optional[str] = None


class JobDescriptionParsed(BaseModel):
    """Structured output from the JD parser."""
    company: str
    title: str
    location: Optional[str] = None
    location_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    skills_required: list[str] = Field(default_factory=list)
    skills_preferred: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    education: Optional[str] = None
    benefits: list[str] = Field(default_factory=list)


class Achievement(BaseModel):
    """A single achievement from the master resume."""
    id: str
    text: str
    tags: list[str] = Field(default_factory=list)
    metrics: Optional[dict] = None
    impact: str = "medium"  # high, medium, low


class GenerationRequest(BaseModel):
    """Input for the AI resume generator."""
    jd_id: int
    model: str = "claude-sonnet-4-5-20241022"
    temperature: float = 0.7
    include_cover_letter: bool = True


class GenerationResult(BaseModel):
    """Output from the AI resume generator."""
    resume_md: str
    cover_letter_md: Optional[str] = None
    achievements_used: list[str] = Field(default_factory=list)
    model_used: str
    prompt_hash: str


class EmailDraft(BaseModel):
    """Email ready for review/sending."""
    recipient: str
    subject: str
    body_html: str
    template_id: Optional[str] = None
    sequence_step: int = 1
