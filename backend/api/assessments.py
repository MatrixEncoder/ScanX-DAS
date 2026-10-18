"""
assessments.py — Assessment API routes for Web Recon, Repository Scan, and Full Assessment.
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
    assessment_type: str = "FULL_ASSESSMENT"
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
    correlated_endpoints: int
    source_mappings: int
    correlation_findings: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class CorrelationOut(BaseModel):
    id: int
    endpoint_url: str
    source_file: str
    confidence: int
    confidence_label: str
    finding_id: Optional[int] = None
    finding_title: str
    finding_severity: str
    model_config = {"from_attributes": True}


class CorrelationEvidenceOut(BaseModel):
    id: int
    signal_type: str
    description: str
    weight: int
    matched: bool
    model_config = {"from_attributes": True}


# ── Background Job ─────────────────────────────────────────────────────────

def _run_assessment_job(assessment_id: int):
    """Background job that runs the full assessment pipeline."""
    from backend.scheduler.job_runner import run_crawl_job
    from backend.api.github_api import _run_analysis_job
    from backend.correlation.engine import CorrelationEngine
    from backend.correlation.source_mapper import build_repo_index

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
        if atype in ("WEB_RECON", "FULL_ASSESSMENT") and assessment.target_url:
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
        if atype in ("REPOSITORY_SCAN", "FULL_ASSESSMENT") and assessment.repo_url:
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

        # ── Phase 3: Correlation (Full Assessment only) ──
        if atype == "FULL_ASSESSMENT" and web_ok and repo_ok and assessment.crawl_id and assessment.analysis_id:
            logger.info(f"[AssessmentJob] {assessment_id} — Running correlation engine")
            try:
                # Get endpoints
                endpoints = db.query(models.Endpoint).filter(
                    models.Endpoint.crawl_id == assessment.crawl_id
                ).all()

                # Get repo files (re-analyze to get file list)
                findings = db.query(models.GithubFinding).filter(
                    models.GithubFinding.analysis_id == assessment.analysis_id
                ).all()

                # Build repo index from findings (we don't have file contents in DB, use file paths)
                # For correlation we work with what we have: endpoint URLs and finding file paths
                repo_index = build_repo_index([], findings)

                # Run correlation
                engine = CorrelationEngine(repo_index)
                corr_results = engine.correlate(endpoints)

                # Persist correlations
                for cr in corr_results:
                    corr = models.Correlation(
                        assessment_id=assessment_id,
                        endpoint_id=cr.endpoint_id,
                        endpoint_url=cr.endpoint_url,
                        source_file=cr.source_file,
                        confidence=cr.confidence,
                        confidence_label=cr.confidence_label,
                        finding_id=cr.finding_id,
                        finding_title=cr.finding_title,
                        finding_severity=cr.finding_severity,
                    )
                    db.add(corr)
                    db.flush()

                    # Persist evidence
                    for ev in cr.evidence:
                        evidence = models.CorrelationEvidence(
                            correlation_id=corr.id,
                            signal_type=ev.get("signal_type", ""),
                            description=ev.get("description", ""),
                            weight=ev.get("weight", 0),
                            matched=ev.get("matched", False),
                        )
                        db.add(evidence)

                assessment.correlated_endpoints = len(endpoints)
                assessment.source_mappings = sum(1 for cr in corr_results if cr.source_file and cr.source_file != "Unknown")
                assessment.correlation_findings = sum(1 for cr in corr_results if cr.finding_id)

                db.commit()
                logger.info(f"[AssessmentJob] {assessment_id} — Correlation complete: "
                             f"{assessment.source_mappings} mappings, {assessment.correlation_findings} findings linked")
            except Exception as e:
                logger.error(f"[AssessmentJob] Correlation error: {e}", exc_info=True)

        # ── Phase 4: Attack Path Generation (Full Assessment only) ──
        if atype == "FULL_ASSESSMENT" and assessment.crawl_id and assessment.analysis_id:
            logger.info(f"[AssessmentJob] {assessment_id} — Generating attack paths")
            try:
                from backend.attack_path.path_generator import AttackPathGenerator

                # Fetch correlations
                correlations = db.query(models.Correlation).filter(
                    models.Correlation.assessment_id == assessment_id
                ).all()
                endpoints = db.query(models.Endpoint).filter(
                    models.Endpoint.crawl_id == assessment.crawl_id
                ).all()
                findings = db.query(models.GithubFinding).filter(
                    models.GithubFinding.analysis_id == assessment.analysis_id
                ).all()

                generator = AttackPathGenerator(correlations, endpoints, findings)
                attack_paths = generator.generate()

                for ap in attack_paths:
                    db_path = models.AttackPath(
                        assessment_id=assessment_id,
                        title=ap.title,
                        description=ap.description,
                        entry_point=ap.entry_point,
                        impact=ap.impact,
                        risk_score=ap.risk_score,
                        risk_label=ap.risk_label,
                        step_count=len(ap.steps),
                    )
                    db.add(db_path)
                    db.flush()

                    for step in ap.steps:
                        db_step = models.AttackPathStep(
                            attack_path_id=db_path.id,
                            step_order=step.step_order,
                            endpoint_url=step.endpoint_url,
                            endpoint_id=step.endpoint_id,
                            finding_title=step.finding_title,
                            finding_severity=step.finding_severity,
                            finding_category=step.finding_category,
                            source_file=step.source_file,
                            confidence=step.confidence,
                            action=step.action,
                            suggestion=step.suggestion,
                        )
                        db.add(db_step)

                db.commit()
                logger.info(f"[AssessmentJob] {assessment_id} — Generated {len(attack_paths)} attack paths")
            except Exception as e:
                logger.error(f"[AssessmentJob] Attack path error: {e}", exc_info=True)

        # ── Finalize ──
        if atype == "WEB_RECON":
            assessment.status = "completed" if web_ok else "failed"
            if not web_ok and not assessment.error_message:
                assessment.error_message = "Web reconnaissance failed"
        elif atype == "REPOSITORY_SCAN":
            assessment.status = "completed" if repo_ok else "failed"
            if not repo_ok and not assessment.error_message:
                assessment.error_message = "Repository analysis failed"
        elif atype == "FULL_ASSESSMENT":
            if web_ok or repo_ok:
                assessment.status = "completed"
            else:
                assessment.status = "failed"
                assessment.error_message = "Both web recon and repository analysis failed"

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


@router.post("/full", response_model=AssessmentOut, status_code=201)
def start_full_assessment(payload: AssessmentCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Start a Full Assessment (Web Recon + Repository Analysis + Correlation)."""
    if not payload.target_url and not payload.repo_url:
        raise HTTPException(status_code=400, detail="Provide at least a target URL or repository URL")
    assessment = models.Assessment(
        assessment_type="FULL_ASSESSMENT",
        target_url=payload.target_url,
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


@router.get("/{assessment_id}/correlations")
def get_correlations(assessment_id: int, db: Session = Depends(get_db)):
    """Get correlation results for an assessment."""
    assessment = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    correlations = db.query(models.Correlation).filter(
        models.Correlation.assessment_id == assessment_id
    ).order_by(models.Correlation.confidence.desc()).all()

    results = []
    for c in correlations:
        evidence = db.query(models.CorrelationEvidence).filter(
            models.CorrelationEvidence.correlation_id == c.id
        ).all()
        results.append({
            "id": c.id,
            "endpoint_url": c.endpoint_url,
            "source_file": c.source_file,
            "confidence": c.confidence,
            "confidence_label": c.confidence_label,
            "finding_id": c.finding_id,
            "finding_title": c.finding_title,
            "finding_severity": c.finding_severity,
            "evidence": [
                {
                    "signal_type": e.signal_type,
                    "description": e.description,
                    "weight": e.weight,
                    "matched": e.matched,
                }
                for e in evidence
            ],
        })

    return {
        "assessment_id": assessment_id,
        "total": len(results),
        "correlated_endpoints": assessment.correlated_endpoints,
        "source_mappings": assessment.source_mappings,
        "correlation_findings": assessment.correlation_findings,
        "correlations": results,
    }


@router.get("/{assessment_id}/attack-paths")
def get_attack_paths(assessment_id: int, db: Session = Depends(get_db)):
    """Get generated attack paths for an assessment."""
    assessment = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    paths = db.query(models.AttackPath).filter(
        models.AttackPath.assessment_id == assessment_id
    ).order_by(models.AttackPath.risk_score.desc()).all()

    results = []
    for p in paths:
        steps = db.query(models.AttackPathStep).filter(
            models.AttackPathStep.attack_path_id == p.id
        ).order_by(models.AttackPathStep.step_order).all()
        results.append({
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "entry_point": p.entry_point,
            "impact": p.impact,
            "risk_score": p.risk_score,
            "risk_label": p.risk_label,
            "step_count": p.step_count,
            "steps": [
                {
                    "step_order": s.step_order,
                    "endpoint_url": s.endpoint_url,
                    "finding_title": s.finding_title,
                    "finding_severity": s.finding_severity,
                    "finding_category": s.finding_category,
                    "source_file": s.source_file,
                    "confidence": s.confidence,
                    "action": s.action,
                    "suggestion": s.suggestion,
                }
                for s in steps
            ],
        })

    return {
        "assessment_id": assessment_id,
        "total": len(results),
        "attack_paths": results,
    }


@router.post("/{assessment_id}/report", response_model=ReportOut, status_code=201)
def generate_assessment_report(assessment_id: int, db: Session = Depends(get_db)):
    """Generate an HTML report for an assessment."""
    assessment = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if assessment.assessment_type == "FULL_ASSESSMENT":
        report_path = os.path.join(REPORTS_DIR, f"assessment_{assessment_id}_full.html")
        _generate_full_report(assessment, db, report_path)
        fmt = "assessment_full_html"
    elif assessment.assessment_type == "WEB_RECON" and assessment.crawl_id:
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
    for fmt in ("assessment_full_html", "assessment_web_html", "assessment_repo_html"):
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


# ── Full Assessment Report Generator ───────────────────────────────────────

def _generate_full_report(assessment, db, output_path):
    """Generate a combined HTML report for full assessment."""
    from jinja2 import Environment, FileSystemLoader
    from datetime import datetime, timezone, timedelta

    templates_dir = os.path.join(BASE_DIR, "backend", "reporting", "templates")
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)

    # Gather data
    crawl = None
    target = None
    endpoints = []
    tech_data = {}
    analysis = None
    findings = []
    correlations = []

    if assessment.crawl_id:
        crawl = db.query(models.CrawlSession).filter(models.CrawlSession.id == assessment.crawl_id).first()
        if crawl:
            target = db.query(models.Target).filter(models.Target.id == crawl.target_id).first()
            endpoints = db.query(models.Endpoint).filter(models.Endpoint.crawl_id == assessment.crawl_id).all()
            if crawl.tech_fingerprint:
                try:
                    tech_data = json.loads(crawl.tech_fingerprint)
                except Exception:
                    pass

    if assessment.analysis_id:
        analysis = db.query(models.GithubAnalysis).filter(models.GithubAnalysis.id == assessment.analysis_id).first()
        findings = db.query(models.GithubFinding).filter(
            models.GithubFinding.analysis_id == assessment.analysis_id
        ).all()

    correlations_db = db.query(models.Correlation).filter(
        models.Correlation.assessment_id == assessment.id
    ).order_by(models.Correlation.confidence.desc()).all()

    for c in correlations_db:
        evidence = db.query(models.CorrelationEvidence).filter(
            models.CorrelationEvidence.correlation_id == c.id
        ).all()
        correlations.append({
            "endpoint_url": c.endpoint_url,
            "source_file": c.source_file,
            "confidence": c.confidence,
            "confidence_label": c.confidence_label,
            "finding_title": c.finding_title,
            "finding_severity": c.finding_severity,
            "evidence": [{"signal_type": e.signal_type, "description": e.description, "matched": e.matched} for e in evidence],
        })

    ist = timezone(timedelta(hours=5, minutes=30))

    context = {
        "assessment": assessment,
        "crawl": crawl,
        "target": target,
        "endpoints": endpoints,
        "tech": tech_data,
        "analysis": analysis,
        "findings": findings,
        "correlations": correlations,
        "generated_at": datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S IST"),
    }

    template_str = _get_full_report_template()
    template = env.from_string(template_str)
    html = template.render(**context)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def _get_full_report_template():
    """Return the HTML template for full assessment reports."""
    template_path = os.path.join(BASE_DIR, "backend", "reporting", "templates", "full_assessment_report.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    # Fallback inline template
    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Scan-X Assessment</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:'Segoe UI',system-ui,sans-serif;background:#0d1117;color:#e6edf3;line-height:1.6}.page{max-width:1200px;margin:0 auto;padding:40px 30px}.header{background:linear-gradient(135deg,#161b22,#1f2937);border-bottom:3px solid #00d4ff;padding:40px;border-radius:12px 12px 0 0}.section{margin-bottom:40px}.section-title{font-size:18px;font-weight:700;color:#58a6ff;border-left:4px solid #00d4ff;padding-left:12px;margin-bottom:20px}.stat-card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px;text-align:center}.stat-card .count{font-size:32px;font-weight:900;color:#00d4ff;display:block}.stat-card .label{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#8b949e;margin-top:4px}.summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:30px 0}.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}.badge-cat{background:rgba(0,212,255,0.15);color:#00d4ff}.badge-conf{background:rgba(124,58,237,0.15);color:#a78bfa}.badge-status{background:rgba(139,148,158,0.15);color:#8b949e}.mono{font-family:'Courier New',monospace;font-size:12px;color:#79c0ff}.table-wrap{overflow-x:auto;border-radius:10px;border:1px solid #30363d}table{width:100%;border-collapse:collapse;font-size:13px}th{background:#161b22;padding:10px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:#8b949e;border-bottom:2px solid #30363d;white-space:nowrap}td{padding:10px 12px;border-bottom:1px solid #21262d;vertical-align:top}tr:hover td{background:#161b22}footer{border-top:1px solid #30363d;padding-top:20px;text-align:center;color:#8b949e;font-size:12px;margin-top:40px}body::after{content:'';position:fixed;top:50%;left:50%;transform:translate(-50%,-50%) rotate(-15deg);width:500px;height:500px;background:url('logo.png') no-repeat center center;background-size:contain;opacity:0.03;pointer-events:none;z-index:0}.page{position:relative;z-index:1}
</style></head><body><div class="page">
<div class="header"><img src="scanx-logo.png" alt="Scan-X" style="height:48px;max-width:120px;object-fit:contain;margin-bottom:8px" />
<div style="font-size:20px;color:#ffffff;margin-top:12px">Security Assessment Report{% if assessment.target_url %} — {{ assessment.target_url }}{% elif assessment.repo_url %} — {{ assessment.repo_url }}{% endif %}</div>
<div style="margin-top:8px;font-size:12px;color:#8b949e">Generated: {{ generated_at }}</div></div>

<section><div class="section-title">Overview</div><div class="summary">
<div class="stat-card"><span class="count">{{ endpoints | length }}</span><div class="label">Endpoints</div></div>
<div class="stat-card"><span class="count">{{ findings | length }}</span><div class="label">Findings</div></div>
<div class="stat-card"><span class="count">{{ correlations | length }}</span><div class="label">Correlations</div></div>
<div class="stat-card"><span class="count">{{ tech | length }}</span><div class="label">Tech Detected</div></div>
</div></section>

{% if correlations %}
<section><div class="section-title">Correlation Results</div>
<div class="table-wrap"><table><thead><tr><th>Endpoint</th><th>Source File</th><th>Finding</th><th>Confidence</th><th>Signals</th></tr></thead>
<tbody>{% for c in correlations %}<tr>
<td class="mono">{{ c.endpoint_url }}</td>
<td class="mono">{{ c.source_file }}</td>
<td>{% if c.finding_title %}<span class="badge badge-cat">{{ c.finding_title }}</span>{% else %}—{% endif %}</td>
<td><span class="badge badge-conf">{{ c.confidence }}%</span></td>
<td>{% for e in c.evidence %}{% if e.matched %}<span style="color:#4ade80;font-size:11px">✓ {{ e.signal_type }}</span>{% endif %} {% endfor %}</td>
</tr>{% endfor %}</tbody></table></div></section>
{% endif %}

{% if findings %}
<section><div class="section-title">Repository Findings</div>
<div class="table-wrap"><table><thead><tr><th>File</th><th>Title</th><th>Rule</th></tr></thead>
<tbody>{% for f in findings %}<tr>
<td class="mono">{{ f.file_path }}</td>
<td>{{ f.title }}</td>
<td style="color:#8b949e;font-size:12px">{{ f.rule_id }}</td>
</tr>{% endfor %}</tbody></table></div></section>
{% endif %}

{% if endpoints %}
<section><div class="section-title">Discovered Endpoints ({{ endpoints | length }})</div>
<div class="table-wrap"><table><thead><tr><th>#</th><th>URL</th><th>Methods</th><th>Status</th><th>Source</th></tr></thead>
<tbody>{% for ep in endpoints %}<tr>
<td style="color:#8b949e">{{ loop.index }}</td>
<td class="mono">{{ ep.url }}</td>
<td>{{ ep.methods }}</td>
<td><span class="badge badge-status">{{ ep.status_code }}</span></td>
<td>{{ ep.source }}</td>
</tr>{% endfor %}</tbody></table></div></section>
{% endif %}

<footer><p>Generated by <strong>Scan-X</strong> for {% if assessment.target_url %}{{ assessment.target_url }}{% else %}{{ assessment.repo_url }}{% endif %} — {{ generated_at }}</p></footer>
</div></body></html>"""
