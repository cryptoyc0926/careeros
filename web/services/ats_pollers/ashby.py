"""Ashby (jobs.ashbyhq.com) poller.

公开 API:  GET https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true
返回 {"jobs": [{id, title, location, jobUrl, ...}]}。
"""
from __future__ import annotations

import json

from services.jd_adapters.base import http_get, FetchError
from .base import Poller, SlugInvalid, instrument, _get_job_lead_cls


class AshbyPoller(Poller):
    name = "ashby"

    @instrument
    def list_jobs(self, filters: dict | None = None) -> list:
        filters = filters or {}
        slug = (filters.get("slug") or "").strip()
        if not slug:
            raise ValueError("AshbyPoller requires filters['slug']")

        api = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
        try:
            body = http_get(api, headers={"Accept": "application/json"})
        except FetchError as e:
            if "HTTP 404" in str(e):
                raise SlugInvalid(slug) from e
            raise

        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            raise ValueError(f"ashby api non-json for {slug}: {e}")

        jobs = data.get("jobs") if isinstance(data, dict) else None
        if not isinstance(jobs, list):
            return []

        JobLead = _get_job_lead_cls()
        q = filters.get("q")
        city = filters.get("city")
        company_name = filters.get("company") or slug

        leads = []
        for j in jobs:
            title = (j.get("title") or "").strip()
            url = (j.get("jobUrl") or j.get("applyUrl") or "").strip()
            location = (j.get("location") or "").strip()
            if not title or not url:
                continue

            if not self._position_matches(title, q):
                continue
            if not self._city_matches(location, city):
                continue

            leads.append(JobLead(
                company=company_name,
                position=title,
                city=location,
                url=url,
                priority=filters.get("priority", "P1"),
                source="ashby",
                direction=filters.get("direction", ""),
                link_type="✅直达",
            ))
        return leads
