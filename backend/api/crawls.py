"""
crawls.py — Crawl session management and job launching API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend import models
from backend.schemas import CrawlCreate, CrawlOut
from backend.scheduler.job_runner import run_crawl_job

router = APIRouter(prefix="/crawls", tags=["Crawls"])


@router.get("/", response_model=List[CrawlOut])
def list_crawls(db: Session = Depends(get_db)):
    return db.query(models.CrawlSession).order_by(models.CrawlSession.created_at.desc()).all()


@router.post("/", response_model=CrawlOut, status_code=201)
def create_crawl(payload: CrawlCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    target = db.query(models.Target).filter(models.Target.id == payload.target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    crawl = models.CrawlSession(
        target_id=payload.target_id,
        max_depth=payload.max_depth,
        max_pages=payload.max_pages,
        status="queued",
    )
    db.add(crawl)
    db.commit()
    db.refresh(crawl)

    background_tasks.add_task(run_crawl_job, crawl.id)
    return crawl


@router.get("/{crawl_id}", response_model=CrawlOut)
def get_crawl(crawl_id: int, db: Session = Depends(get_db)):
    crawl = db.query(models.CrawlSession).filter(models.CrawlSession.id == crawl_id).first()
    if not crawl:
        raise HTTPException(status_code=404, detail="Crawl session not found")
    return crawl


@router.post("/{crawl_id}/cancel", response_model=CrawlOut)
def cancel_crawl(crawl_id: int, db: Session = Depends(get_db)):
    crawl = db.query(models.CrawlSession).filter(models.CrawlSession.id == crawl_id).first()
    if not crawl:
        raise HTTPException(status_code=404, detail="Crawl session not found")
    if crawl.status not in ("queued", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel crawl in status '{crawl.status}'")
    crawl.status = "failed"
    crawl.error_message = "Cancelled by user"
    db.commit()
    db.refresh(crawl)
    return crawl
