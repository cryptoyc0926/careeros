"""Lever (jobs.lever.co) poller.

公开 API:  GET https://api.lever.co/v0/postings/{slug}?mode=json
返回的每个 posting 自带 hostedUrl（直达 JD 详情），无需额外抓取。
"""
from __future__ import annotations

import json
from typing import Any

from services.jd_adapters.base import http_get, FetchError
from .base import Poller, SlugInvalid, instrument, _get_job_lead_cls


class LeverPoller(Poller):
    name = "lever"

    @instrument
    def list_jobs(self, filters: dict | None = None) -> list:
        filters = filters or {}
        slug = (filters.get("slug") or "").strip()
        if not slug:
            raise ValueError("LeverPoller requires filters['slug']")

        api = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        try:
            body = http_get(api, headers={"Accept": "application/json"})
        except FetchError as e:
            if "HTTP 404" in str(e):
                raise SlugInvalid(slug) from e
            raise

        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            raise ValueError(f"lever api returned non-json for {slug}: {e}")

        if not isinstance(data, list):
            return []

        JobLead = _get_job_lead_cls()
        q = filters.get("q")
        city = filters.get("city")
        company_name = filters.get("company") or slug

        leads = []
        for it in data:
            title = (it.get("text") or "").strip()
            if not title:
                continue
            categories: dict[str, Any] = it.get("categories") or {}
            location = (categories.get("location") or "").strip()
            hosted_url = (it.get("hostedUrl") or "").strip()
            if not hosted_url:
                continue

            if not self._position_matches(title, q):
                continue
            if not self._city_matches(location, city):
                continue

            leads.append(JobLead(
                company=company_name,
                position=title,
                city=location,
                url=hosted_url,
                priority=filters.get("priority", "P1"),
                source="lever",
                direction=filters.get("direction", ""),
                link_type="✅直达",
            ))
        return leads
