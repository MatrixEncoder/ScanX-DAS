"""
github_api.py — GitHub repository analysis API routes.
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

router = APIRouter(prefix="/github", tags=["GitHub Analysis"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.path.join(BASE_DIR, "database", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


# ── Schemas ────────────────────────────────────────────────────────────────

class GithubAnalysisCreate(BaseModel):
    repo_url: str
    pat: str = ""  # Personal Access Token (optional for public repos)
    branch: str = "main"


class GithubAnalysisOut(BaseModel):
    id: int
    repo_url: str
    repo_name: str
    branch: str
    status: str
    error_message: Optional[str] = None
    total_files: int
    files_scanned: int
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    analysis_duration: float
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class GithubFindingOut(BaseModel):
    id: int
    file_path: str
    line_number: int
    end_line: int
    language: str
    rule_id: str
    severity: str
    category: str
    title: str
    description: str
    evidence: str
    recommendation: str
    model_config = {"from_attributes": True}


# ── Background Job ─────────────────────────────────────────────────────────

def _run_analysis_job(analysis_id: int, repo_url: str, pat: str, branch: str):
    """Background job that runs the full GitHub analysis."""
    from backend.github_analyzer.analyzer import RepoAnalyzer

    db = SessionLocal()
    try:
        analysis = db.query(models.GithubAnalysis).filter(
            models.GithubAnalysis.id == analysis_id
        ).first()
        if not analysis:
            logger.error(f"[GitHubJob] Analysis {analysis_id} not found")
            return

        analysis.status = "scanning"
        analysis.started_at = datetime.now(timezone.utc)
        db.commit()

        # Run analyzer
        analyzer = RepoAnalyzer(token=pat if pat else None)
        result = analyzer.analyze(repo_url, branch=branch)

        # Check for fatal errors (e.g. rate limit, repo not found)
        if result.errors and result.files_analyzed == 0:
            analysis.status = "failed"
            analysis.error_message = "; ".join(result.errors)[:500]
            analysis.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.error(f"[GitHubJob] Analysis {analysis_id} failed: {analysis.error_message}")
            return

        # Persist findings
        for finding in result.findings:
            db_finding = models.GithubFinding(
                analysis_id=analysis_id,
                file_path=finding.file_path,
                line_number=finding.line_number,
                end_line=finding.end_line,
                language=finding.language,
                rule_id=finding.rule_id,
                severity=finding.severity,
                category=finding.category,
                title=finding.title,
                description=finding.description,
                evidence=finding.evidence,
                recommendation=finding.recommendation,
            )
            db.add(db_finding)

        # Update analysis stats
        analysis.status = "completed"
        analysis.completed_at = datetime.now(timezone.utc)
        analysis.total_files = result.total_files
        analysis.files_scanned = result.files_analyzed
        analysis.total_findings = len(result.findings)
        analysis.critical_count = result.critical_count
        analysis.high_count = result.high_count
        analysis.medium_count = result.medium_count
        analysis.low_count = result.low_count
        analysis.info_count = result.info_count
        analysis.analysis_duration = result.duration

        db.commit()
        logger.info(
            f"[GitHubJob] Analysis {analysis_id} completed: "
            f"{len(result.findings)} findings in {result.duration}s"
        )

    except Exception as e:
        logger.error(f"[GitHubJob] Analysis {analysis_id} failed: {e}", exc_info=True)
        try:
            a = db.query(models.GithubAnalysis).filter(
                models.GithubAnalysis.id == analysis_id
            ).first()
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

@router.get("/analyses", response_model=List[GithubAnalysisOut])
def list_analyses(db: Session = Depends(get_db)):
    return db.query(models.GithubAnalysis).order_by(
        models.GithubAnalysis.created_at.desc()
    ).all()


@router.post("/analyze", response_model=GithubAnalysisOut, status_code=201)
def start_analysis(payload: GithubAnalysisCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Start a new GitHub repository security analysis."""
    analysis = models.GithubAnalysis(
        repo_url=payload.repo_url,
        repo_name=payload.repo_url.rstrip("/").split("/")[-1].replace(".git", ""),
        branch=payload.branch,
        status="queued",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    background_tasks.add_task(_run_analysis_job, analysis.id, payload.repo_url, payload.pat, payload.branch)
    return analysis


@router.get("/analyses/{analysis_id}", response_model=GithubAnalysisOut)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.query(models.GithubAnalysis).filter(
        models.GithubAnalysis.id == analysis_id
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.get("/analyses/{analysis_id}/findings", response_model=List[GithubFindingOut])
def get_findings(
    analysis_id: int,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get findings for an analysis, optionally filtered by severity/category."""
    q = db.query(models.GithubFinding).filter(
        models.GithubFinding.analysis_id == analysis_id
    )
    if severity:
        q = q.filter(models.GithubFinding.severity == severity)
    if category:
        q = q.filter(models.GithubFinding.category == category)
    return q.order_by(models.GithubFinding.severity, models.GithubFinding.file_path).all()


@router.delete("/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.query(models.GithubAnalysis).filter(
        models.GithubAnalysis.id == analysis_id
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    db.delete(analysis)
    db.commit()


@router.post("/analyses/{analysis_id}/report", response_model=ReportOut, status_code=201)
def generate_report(analysis_id: int, db: Session = Depends(get_db)):
    """Generate an HTML report for a GitHub analysis."""
    from backend.github_analyzer.report_generator import generate_github_report

    analysis = db.query(models.GithubAnalysis).filter(
        models.GithubAnalysis.id == analysis_id
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    findings = db.query(models.GithubFinding).filter(
        models.GithubFinding.analysis_id == analysis_id
    ).order_by(
        models.GithubFinding.severity, models.GithubFinding.file_path
    ).all()

    report_path = os.path.join(REPORTS_DIR, f"github_analysis_{analysis_id}.html")
    generate_github_report(analysis, findings, report_path)

    # Upsert report record
    existing = db.query(models.Report).filter(
        models.Report.crawl_id == analysis_id,
        models.Report.format == "github_html",
    ).first()
    if existing:
        existing.filepath = report_path
        db.commit()
        db.refresh(existing)
        report = existing
    else:
        report = models.Report(
            crawl_id=analysis_id,
            format="github_html",
            filepath=report_path,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

    return report


@router.get("/analyses/{analysis_id}/report/download")
def download_report(analysis_id: int, db: Session = Depends(get_db)):
    """Download the HTML report for a GitHub analysis."""
    report = db.query(models.Report).filter(
        models.Report.crawl_id == analysis_id,
        models.Report.format == "github_html",
    ).first()
    if not report or not os.path.exists(report.filepath):
        raise HTTPException(status_code=404, detail="Report not found. Generate it first.")
    return FileResponse(
        report.filepath,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="github_analysis_{analysis_id}.html"'},
    )
