"""
endpoints.py — Discovered endpoints query API routes.
"""

import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from backend.database import get_db
from backend import models
from backend.schemas import EndpointOut, DashboardStats, CrawlOut

router = APIRouter(prefix="/endpoints", tags=["Endpoints"])


@router.get("/", response_model=List[EndpointOut])
def list_endpoints(
    crawl_id: Optional[int] = Query(None),
    target_id: Optional[int] = Query(None),
    source: Optional[str] = Query(None),
    is_api: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(models.Endpoint)
    if crawl_id:
        q = q.filter(models.Endpoint.crawl_id == crawl_id)
    if target_id:
        q = q.filter(models.Endpoint.target_id == target_id)
    if source:
        q = q.filter(models.Endpoint.source == source)
    if is_api is not None:
        q = q.filter(models.Endpoint.is_api == is_api)
    if search:
        q = q.filter(models.Endpoint.url.ilike(f"%{search}%"))
    return q.order_by(models.Endpoint.status_code, models.Endpoint.url).all()


@router.get("/stats")
def endpoint_stats(crawl_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(models.Endpoint)
    if crawl_id:
        q = q.filter(models.Endpoint.crawl_id == crawl_id)
    eps = q.all()

    sources = {}
    for ep in eps:
        sources[ep.source] = sources.get(ep.source, 0) + 1

    return {
        "total": len(eps),
        "api_endpoints": sum(1 for e in eps if e.is_api),
        "login_forms": sum(1 for e in eps if e.has_login_form),
        "with_params": sum(1 for e in eps if e.parameters),
        "by_source": sources,
        "by_status": _status_breakdown(eps),
    }


def _status_breakdown(endpoints):
    counts = {}
    for ep in endpoints:
        bucket = f"{ep.status_code // 100}xx"
        counts[bucket] = counts.get(bucket, 0) + 1
    return counts


@router.get("/dashboard", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db)):
    targets = db.query(models.Target).count()
    crawls = db.query(models.CrawlSession).count()
    endpoints = db.query(models.Endpoint).count()
    api_eps = db.query(models.Endpoint).filter(models.Endpoint.is_api == True).count()
    login_forms = db.query(models.Endpoint).filter(models.Endpoint.has_login_form == True).count()

    recent_crawls = (
        db.query(models.CrawlSession)
        .order_by(models.CrawlSession.created_at.desc())
        .limit(5)
        .all()
    )

    # Assessment stats
    web_assessments = db.query(models.Assessment).filter(models.Assessment.assessment_type == "WEB_RECON").count()
    repo_assessments = db.query(models.Assessment).filter(models.Assessment.assessment_type == "REPOSITORY_SCAN").count()
    full_assessments = db.query(models.Assessment).filter(models.Assessment.assessment_type == "FULL_ASSESSMENT").count()

    # Correlation stats (only from full assessments)
    correlated_endpoints = 0
    source_mappings = 0
    correlation_findings = 0
    for a in db.query(models.Assessment).filter(models.Assessment.assessment_type == "FULL_ASSESSMENT").all():
        correlated_endpoints += a.correlated_endpoints
        source_mappings += a.source_mappings
        correlation_findings += a.correlation_findings

    # Endpoint source breakdown
    all_endpoints = db.query(models.Endpoint).all()
    by_source = {}
    for ep in all_endpoints:
        by_source[ep.source] = by_source.get(ep.source, 0) + 1

    # Endpoint method breakdown
    by_method = {}
    for ep in all_endpoints:
        for m in (ep.methods or "").split(","):
            m = m.strip()
            if m:
                by_method[m] = by_method.get(m, 0) + 1

    # Crawl status breakdown
    completed_crawls = db.query(models.CrawlSession).filter(models.CrawlSession.status == "completed").count()
    failed_crawls = db.query(models.CrawlSession).filter(models.CrawlSession.status == "failed").count()
    running_crawls = db.query(models.CrawlSession).filter(models.CrawlSession.status == "running").count()

    return DashboardStats(
        total_targets=targets,
        total_crawls=crawls,
        total_endpoints=endpoints,
        api_endpoints=api_eps,
        login_forms=login_forms,
        recent_crawls=[CrawlOut.model_validate(c) for c in recent_crawls],
        web_assessments=web_assessments,
        repo_assessments=repo_assessments,
        full_assessments=full_assessments,
        correlated_endpoints=correlated_endpoints,
        source_mappings=source_mappings,
        correlation_findings=correlation_findings,
        endpoints_by_source=by_source,
        endpoints_by_method=by_method,
        completed_crawls=completed_crawls,
        failed_crawls=failed_crawls,
        running_crawls=running_crawls,
    )


@router.get("/{endpoint_id}", response_model=EndpointOut)
def get_endpoint(endpoint_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    ep = db.query(models.Endpoint).filter(models.Endpoint.id == endpoint_id).first()
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return ep
