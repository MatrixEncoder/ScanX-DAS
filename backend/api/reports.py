"""
reports.py — Report generation and download API routes.
"""

import os
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend import models
from backend.schemas import ReportOut
from backend.reporting.endpoint_report import generate_endpoint_report

router = APIRouter(prefix="/reports", tags=["Reports"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.path.join(BASE_DIR, "database", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


@router.post("/{crawl_id}/generate", response_model=List[ReportOut], status_code=201)
def generate_reports(crawl_id: int, db: Session = Depends(get_db)):
    crawl = db.query(models.CrawlSession).filter(models.CrawlSession.id == crawl_id).first()
    if not crawl:
        raise HTTPException(status_code=404, detail="Crawl session not found")

    target = db.query(models.Target).filter(models.Target.id == crawl.target_id).first()
    endpoints = (
        db.query(models.Endpoint)
        .filter(models.Endpoint.crawl_id == crawl_id)
        .order_by(models.Endpoint.url)
        .all()
    )

    # Parse tech fingerprint
    tech_data = {}
    if crawl.tech_fingerprint:
        try:
            tech_data = json.loads(crawl.tech_fingerprint)
        except Exception:
            pass

    reports_created = []

    # HTML report
    html_path = os.path.join(REPORTS_DIR, f"crawl_{crawl_id}_report.html")
    generate_endpoint_report(crawl, target, endpoints, tech_data, html_path)
    html_report = _upsert_report(db, crawl_id, "html", html_path)
    reports_created.append(html_report)

    return reports_created


@router.get("/{crawl_id}", response_model=List[ReportOut])
def list_reports(crawl_id: int, db: Session = Depends(get_db)):
    return db.query(models.Report).filter(models.Report.crawl_id == crawl_id).all()


@router.get("/{crawl_id}/download/{format}")
def download_report(crawl_id: int, format: str, db: Session = Depends(get_db)):
    if format not in ("html",):
        raise HTTPException(status_code=400, detail="Format must be 'html'")
    report = (
        db.query(models.Report)
        .filter(models.Report.crawl_id == crawl_id, models.Report.format == format)
        .first()
    )
    if not report or not os.path.exists(report.filepath):
        raise HTTPException(status_code=404, detail="Report not found - generate it first")
    return FileResponse(
        report.filepath,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{os.path.basename(report.filepath)}"'},
    )


def _upsert_report(db: Session, crawl_id: int, fmt: str, filepath: str) -> models.Report:
    existing = db.query(models.Report).filter(
        models.Report.crawl_id == crawl_id, models.Report.format == fmt
    ).first()
    if existing:
        existing.filepath = filepath
        db.commit()
        db.refresh(existing)
        return existing
    r = models.Report(crawl_id=crawl_id, format=fmt, filepath=filepath)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r
