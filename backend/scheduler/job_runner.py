"""
job_runner.py — Crawl job orchestrator.

Runs the full endpoint discovery pipeline:
  1. Deep crawl (BFS + forms + JS + hidden paths)
  2. Tech fingerprinting
  3. Persist results to DB
"""

import json
import logging
from datetime import datetime, timezone

from backend.database import SessionLocal
from backend import models
from backend.crawler.deep_crawler import DeepCrawler
from backend.fingerprinter.tech_detect import TechFingerprinter

logger = logging.getLogger(__name__)


def run_crawl_job(crawl_id: int):
    """Execute the full crawl pipeline as a background task."""
    db = SessionLocal()
    try:
        crawl = db.query(models.CrawlSession).filter(models.CrawlSession.id == crawl_id).first()
        if not crawl:
            logger.error(f"[Job] Crawl {crawl_id} not found")
            return

        target = db.query(models.Target).filter(models.Target.id == crawl.target_id).first()
        if not target:
            _fail_crawl(db, crawl, "Target not found")
            return

        # ── Mark as running ──
        crawl.status = "running"
        crawl.started_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"[Job] Crawl {crawl_id} started for {target.base_url}")

        # ── Phase 1: Deep Crawl ──
        try:
            crawler = DeepCrawler(
                target_url=target.base_url,
                max_depth=crawl.max_depth,
                max_pages=crawl.max_pages,
            )
            crawl_result = crawler.crawl()
        except Exception as e:
            logger.error(f"[Job] Crawl failed: {e}")
            _fail_crawl(db, crawl, str(e))
            return

        # ── Phase 2: Tech Fingerprinting ──
        try:
            fingerprinter = TechFingerprinter()
            fingerprint = fingerprinter.fingerprint(target.base_url)
            fp_data = {
                "server": fingerprint.server,
                "language": fingerprint.language,
                "frameworks": fingerprint.frameworks,
                "cms": fingerprint.cms,
                "js_libraries": fingerprint.js_libraries,
                "security_headers": fingerprint.security_headers,
            }
            crawl.tech_fingerprint = json.dumps(fp_data)
        except Exception as e:
            logger.warning(f"[Job] Fingerprinting failed: {e}")
            crawl.tech_fingerprint = json.dumps({})

        # ── Phase 3: Persist Endpoints ──
        for ep in crawl_result.endpoints:
            endpoint = models.Endpoint(
                target_id=target.id,
                crawl_id=crawl.id,
                url=ep.url,
                methods=",".join(ep.methods),
                status_code=ep.status_code,
                content_type=ep.content_type,
                content_length=ep.content_length,
                title=ep.title,
                redirect_url=ep.redirect_url,
                parameters=json.dumps(ep.parameters) if ep.parameters else None,
                form_count=ep.form_count,
                source=ep.source,
                depth=ep.depth,
                is_api=ep.is_api,
                has_login_form=ep.has_login_form,
            )
            db.add(endpoint)

        # ── Update crawl stats ──
        crawl.status = "completed"
        crawl.completed_at = datetime.now(timezone.utc)
        crawl.total_endpoints = len(crawl_result.endpoints)
        crawl.total_requests = crawl_result.total_requests
        crawl.crawl_duration = crawl_result.crawl_duration
        crawl.pages_crawled = crawl_result.pages_crawled
        crawl.forms_found = crawl_result.forms_found

        db.commit()
        logger.info(
            f"[Job] Crawl {crawl_id} completed: "
            f"{len(crawl_result.endpoints)} endpoints in {crawl_result.crawl_duration}s"
        )

    except Exception as e:
        logger.error(f"[Job] Crawl {crawl_id} failed: {e}", exc_info=True)
        try:
            _fail_crawl(db, db.query(models.CrawlSession).filter(models.CrawlSession.id == crawl_id).first(), str(e))
        except Exception:
            pass
    finally:
        db.close()


def _fail_crawl(db, crawl, message: str):
    if crawl:
        crawl.status = "failed"
        crawl.error_message = message[:500]
        crawl.completed_at = datetime.now(timezone.utc)
        db.commit()
