"""
assessments.py — Assessment API routes for Web Recon and Repository Scan.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db, SessionLocal
from backend import models
from backend.schemas import ReportOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assessments", tags=["Assessments"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.path.join(BASE_DIR, "database", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


# ── Schemas ────────────────────────────────────────────────────────────────

class AssessmentCreate(BaseModel):
    assessment_type: str = "WEB_RECON"
    target_url: str = ""
    repo_url: str = ""
    pat: str = ""
    branch: str = "main"


class AssessmentOut(BaseModel):
    id: int
    assessment_type: str
    status: str
    error_message: Optional[str] = None
    target_url: Optional[str] = None
    repo_url: Optional[str] = None
    branch: str
    crawl_id: Optional[int] = None
    analysis_id: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ── Background Job ─────────────────────────────────────────────────────────

def _run_assessment_job(assessment_id: int):
    """Background job that runs the assessment pipeline (web recon and/or repo analysis)."""
    from backend.scheduler.job_runner import run_crawl_job
    from backend.api.github_api import _run_analysis_job

    db = SessionLocal()
    try:
        assessment = db.query(models.Assessment).filter(
            models.Assessment.id == assessment_id
        ).first()
        if not assessment:
            logger.error(f"[AssessmentJob] Assessment {assessment_id} not found")
            return

        assessment.status = "running"
        assessment.started_at = datetime.now(timezone.utc)
        db.commit()

        atype = assessment.assessment_type
        web_ok = True
        repo_ok = True

        # ── Phase 1: Web Recon (if needed) ──
        if atype == "WEB_RECON" and assessment.target_url:
            logger.info(f"[AssessmentJob] {assessment_id} — Starting web recon for {assessment.target_url}")
            try:
                # Create target
                url = assessment.target_url.strip()
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                target = models.Target(name=url.split("//")[-1].split("/")[0], base_url=url)
                db.add(target)
                db.commit()
                db.refresh(target)

                # Create and run crawl
                crawl = models.CrawlSession(
                    target_id=target.id,
                    max_depth=2,
                    max_pages=80,
                    status="queued",
                )
                db.add(crawl)
                db.commit()
                db.refresh(crawl)

                assessment.crawl_id = crawl.id
                db.commit()

                run_crawl_job(crawl.id)

                # Re-check crawl status
                db.refresh(crawl)
                if crawl.status != "completed":
                    web_ok = False
                    logger.warning(f"[AssessmentJob] Web recon failed: {crawl.error_message}")
            except Exception as e:
                web_ok = False
                logger.error(f"[AssessmentJob] Web recon error: {e}")

        # ── Phase 2: Repository Analysis (if needed) ──
        if atype == "REPOSITORY_SCAN" and assessment.repo_url:
            logger.info(f"[AssessmentJob] {assessment_id} — Starting repo analysis for {assessment.repo_url}")
            try:
                analysis = models.GithubAnalysis(
                    repo_url=assessment.repo_url,
                    repo_name=assessment.repo_url.rstrip("/").split("/")[-1].replace(".git", ""),
                    branch=assessment.branch,
                    status="queued",
                )
                db.add(analysis)
                db.commit()
                db.refresh(analysis)

                assessment.analysis_id = analysis.id
                db.commit()

                _run_analysis_job(analysis.id, assessment.repo_url, assessment.pat or "", assessment.branch)

                db.refresh(analysis)
                if analysis.status != "completed":
                    repo_ok = False
                    logger.warning(f"[AssessmentJob] Repo analysis failed: {analysis.error_message}")
            except Exception as e:
                repo_ok = False
                logger.error(f"[AssessmentJob] Repo analysis error: {e}")

        # ── Finalize ──
        if atype == "WEB_RECON":
            assessment.status = "completed" if web_ok else "failed"
            if not web_ok and not assessment.error_message:
                assessment.error_message = "Web reconnaissance failed"
        elif atype == "REPOSITORY_SCAN":
            assessment.status = "completed" if repo_ok else "failed"
            if not repo_ok and not assessment.error_message:
                assessment.error_message = "Repository analysis failed"

        assessment.completed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"[AssessmentJob] {assessment_id} completed: {assessment.status}")

    except Exception as e:
        logger.error(f"[AssessmentJob] Assessment {assessment_id} failed: {e}", exc_info=True)
        try:
            a = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
            if a:
                a.status = "failed"
                a.error_message = str(e)[:500]
                a.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ── Routes ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[AssessmentOut])
def list_assessments(db: Session = Depends(get_db)):
    return db.query(models.Assessment).order_by(models.Assessment.created_at.desc()).all()


@router.post("/web", response_model=AssessmentOut, status_code=201)
def start_web_recon(target_url: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Start a Web Recon Only assessment."""
    assessment = models.Assessment(
        assessment_type="WEB_RECON",
        target_url=target_url,
        status="queued",
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    background_tasks.add_task(_run_assessment_job, assessment.id)
    return assessment


@router.post("/repository", response_model=AssessmentOut, status_code=201)
def start_repo_scan(payload: AssessmentCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Start a Repository Analysis Only assessment."""
    assessment = models.Assessment(
        assessment_type="REPOSITORY_SCAN",
        repo_url=payload.repo_url,
        pat=payload.pat,
        branch=payload.branch,
        status="queued",
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    background_tasks.add_task(_run_assessment_job, assessment.id)
    return assessment


@router.get("/{assessment_id}", response_model=AssessmentOut)
def get_assessment(assessment_id: int, db: Session = Depends(get_db)):
    assessment = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


@router.get("/{assessment_id}/status", response_model=AssessmentOut)
def get_assessment_status(assessment_id: int, db: Session = Depends(get_db)):
    assessment = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


@router.post("/{assessment_id}/report", response_model=ReportOut, status_code=201)
def generate_assessment_report(assessment_id: int, db: Session = Depends(get_db)):
    """Generate an HTML report for an assessment."""
    assessment = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if assessment.assessment_type == "WEB_RECON" and assessment.crawl_id:
        # Delegate to existing report generator
        from backend.reporting.endpoint_report import generate_endpoint_report
        crawl = db.query(models.CrawlSession).filter(models.CrawlSession.id == assessment.crawl_id).first()
        target = db.query(models.Target).filter(models.Target.id == crawl.target_id).first() if crawl else None
        endpoints = db.query(models.Endpoint).filter(models.Endpoint.crawl_id == assessment.crawl_id).all()
        tech_data = json.loads(crawl.tech_fingerprint) if crawl and crawl.tech_fingerprint else {}
        report_path = os.path.join(REPORTS_DIR, f"assessment_{assessment_id}_web.html")
        if crawl and target:
            generate_endpoint_report(crawl, target, endpoints, tech_data, report_path)
        fmt = "assessment_web_html"
    elif assessment.assessment_type == "REPOSITORY_SCAN" and assessment.analysis_id:
        from backend.github_analyzer.report_generator import generate_github_report
        analysis = db.query(models.GithubAnalysis).filter(models.GithubAnalysis.id == assessment.analysis_id).first()
        findings = db.query(models.GithubFinding).filter(models.GithubFinding.analysis_id == assessment.analysis_id).all()
        report_path = os.path.join(REPORTS_DIR, f"assessment_{assessment_id}_repo.html")
        if analysis:
            generate_github_report(analysis, findings, report_path)
        fmt = "assessment_repo_html"
    else:
        raise HTTPException(status_code=400, detail="No results to report — run the assessment first")

    # Upsert report record using crawl_id as assessment_id placeholder
    existing = db.query(models.Report).filter(
        models.Report.crawl_id == assessment_id,
        models.Report.format == fmt,
    ).first()
    if existing:
        existing.filepath = report_path
        db.commit()
        db.refresh(existing)
        report = existing
    else:
        report = models.Report(crawl_id=assessment_id, format=fmt, filepath=report_path)
        db.add(report)
        db.commit()
        db.refresh(report)

    return report


@router.get("/{assessment_id}/report/download")
def download_assessment_report(assessment_id: int, db: Session = Depends(get_db)):
    """Download the HTML report for an assessment."""
    # Try all report formats
    for fmt in ("assessment_web_html", "assessment_repo_html"):
        report = db.query(models.Report).filter(
            models.Report.crawl_id == assessment_id,
            models.Report.format == fmt,
        ).first()
        if report and os.path.exists(report.filepath):
            return FileResponse(
                report.filepath,
                media_type="text/html",
                headers={"Content-Disposition": f'attachment; filename="assessment_{assessment_id}.html"'},
            )
    raise HTTPException(status_code=404, detail="Report not found. Generate it first.")


@router.delete("/{assessment_id}", status_code=204)
def delete_assessment(assessment_id: int, db: Session = Depends(get_db)):
    assessment = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    db.delete(assessment)
    db.commit()
