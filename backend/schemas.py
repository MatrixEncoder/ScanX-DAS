"""
schemas.py — Pydantic v2 request/response schemas for the Scan-X API.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ── Target ────────────────────────────────────────────────────────────────

class TargetCreate(BaseModel):
    name: str
    base_url: str
    notes: str = ""


class TargetOut(BaseModel):
    id: int
    name: str
    base_url: str
    notes: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Crawl Session ─────────────────────────────────────────────────────────

class CrawlCreate(BaseModel):
    target_id: int
    max_depth: int = 4
    max_pages: int = 200


class CrawlOut(BaseModel):
    id: int
    target_id: int
    status: str
    max_depth: int
    max_pages: int
    total_endpoints: int
    total_requests: int
    crawl_duration: float
    pages_crawled: int
    forms_found: int
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ── Endpoint ──────────────────────────────────────────────────────────────

class EndpointOut(BaseModel):
    id: int
    url: str
    methods: str
    status_code: int
    content_type: str
    title: str
    redirect_url: str
    parameters: Optional[str] = None
    form_count: int
    source: str
    depth: int
    is_api: bool
    has_login_form: bool
    discovered_at: datetime
    model_config = {"from_attributes": True}


# ── Dashboard ─────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_targets: int
    total_crawls: int
    total_endpoints: int
    api_endpoints: int
    login_forms: int
    recent_crawls: List[CrawlOut]
    # Assessment stats
    web_assessments: int = 0
    repo_assessments: int = 0
    full_assessments: int = 0
    correlated_endpoints: int = 0
    source_mappings: int = 0
    correlation_findings: int = 0
    # Dashboard charts
    endpoints_by_source: dict = {}
    endpoints_by_method: dict = {}
    completed_crawls: int = 0
    failed_crawls: int = 0
    running_crawls: int = 0


# ── Report ────────────────────────────────────────────────────────────────

class ReportOut(BaseModel):
    id: int
    crawl_id: int
    format: str
    filepath: str
    generated_at: datetime
    model_config = {"from_attributes": True}
