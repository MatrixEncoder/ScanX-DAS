"""
models.py — SQLAlchemy ORM models for the endpoint discovery platform.
"""

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, Text, Boolean, ForeignKey, Integer
import datetime
from datetime import timezone as tz

from backend.database import Base


class Target(Base):
    """A web application registered for crawling."""
    __tablename__ = "targets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    base_url: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(default=lambda: datetime.datetime.now(tz.utc))

    crawls: Mapped[list["CrawlSession"]] = relationship("CrawlSession", back_populates="target", cascade="all, delete-orphan")
    endpoints: Mapped[list["Endpoint"]] = relationship("Endpoint", back_populates="target", cascade="all, delete-orphan")


class CrawlSession(Base):
    """A crawling session against a target."""
    __tablename__ = "crawl_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("targets.id", ondelete="CASCADE"), index=True)

    status: Mapped[str] = mapped_column(String(50), default="created")  # created, queued, running, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Crawl config
    max_depth: Mapped[int] = mapped_column(default=4)
    max_pages: Mapped[int] = mapped_column(default=200)

    # Stats
    total_endpoints: Mapped[int] = mapped_column(default=0)
    total_requests: Mapped[int] = mapped_column(default=0)
    crawl_duration: Mapped[float] = mapped_column(Float, default=0.0)
    pages_crawled: Mapped[int] = mapped_column(default=0)
    forms_found: Mapped[int] = mapped_column(default=0)

    # Tech fingerprint (JSON string)
    tech_fingerprint: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(default=lambda: datetime.datetime.now(tz.utc))
    started_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)

    target: Mapped["Target"] = relationship("Target", back_populates="crawls")
    endpoints: Mapped[list["Endpoint"]] = relationship("Endpoint", back_populates="crawl", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="crawl", cascade="all, delete-orphan")


class Endpoint(Base):
    """A discovered URL endpoint."""
    __tablename__ = "endpoints"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("targets.id", ondelete="CASCADE"), index=True)
    crawl_id: Mapped[int] = mapped_column(ForeignKey("crawl_sessions.id", ondelete="CASCADE"), index=True)

    url: Mapped[str] = mapped_column(String(2048))
    methods: Mapped[str] = mapped_column(String(100), default="GET")  # Comma-separated: GET,POST,PUT
    status_code: Mapped[int] = mapped_column(default=0)
    content_type: Mapped[str] = mapped_column(String(255), default="")
    content_length: Mapped[int] = mapped_column(default=0)
    title: Mapped[str] = mapped_column(String(500), default="")
    redirect_url: Mapped[str] = mapped_column(String(2048), default="")
    parameters: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    form_count: Mapped[int] = mapped_column(default=0)
    source: Mapped[str] = mapped_column(String(50), default="link")  # link, form, js, wordlist
    depth: Mapped[int] = mapped_column(default=0)
    is_api: Mapped[bool] = mapped_column(Boolean, default=False)
    has_login_form: Mapped[bool] = mapped_column(Boolean, default=False)
    discovered_at: Mapped[datetime.datetime] = mapped_column(default=lambda: datetime.datetime.now(tz.utc))

    target: Mapped["Target"] = relationship("Target", back_populates="endpoints")
    crawl: Mapped["CrawlSession"] = relationship("CrawlSession", back_populates="endpoints")


class Report(Base):
    """Generated endpoint reports."""
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    crawl_id: Mapped[int] = mapped_column(ForeignKey("crawl_sessions.id", ondelete="CASCADE"), index=True)
    format: Mapped[str] = mapped_column(String(10))  # html
    filepath: Mapped[str] = mapped_column(String(512))
    generated_at: Mapped[datetime.datetime] = mapped_column(default=lambda: datetime.datetime.now(tz.utc))

    crawl: Mapped["CrawlSession"] = relationship("CrawlSession", back_populates="reports")


# ── GitHub Analysis ─────────────────────────────────────────────────────────

class GithubAnalysis(Base):
    """A GitHub repository security analysis job."""
    __tablename__ = "github_analyses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    repo_url: Mapped[str] = mapped_column(String(512), index=True)
    repo_name: Mapped[str] = mapped_column(String(255), default="")
    branch: Mapped[str] = mapped_column(String(255), default="main")

    status: Mapped[str] = mapped_column(String(50), default="queued")  # queued, cloning, scanning, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Stats
    total_files: Mapped[int] = mapped_column(default=0)
    files_scanned: Mapped[int] = mapped_column(default=0)
    total_findings: Mapped[int] = mapped_column(default=0)
    critical_count: Mapped[int] = mapped_column(default=0)
    high_count: Mapped[int] = mapped_column(default=0)
    medium_count: Mapped[int] = mapped_column(default=0)
    low_count: Mapped[int] = mapped_column(default=0)
    info_count: Mapped[int] = mapped_column(default=0)
    analysis_duration: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime.datetime] = mapped_column(default=lambda: datetime.datetime.now(tz.utc))
    started_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)

    findings: Mapped[list["GithubFinding"]] = relationship("GithubFinding", back_populates="analysis", cascade="all, delete-orphan")


class GithubFinding(Base):
    """A single security finding in a GitHub repo file."""
    __tablename__ = "github_findings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("github_analyses.id", ondelete="CASCADE"), index=True)

    file_path: Mapped[str] = mapped_column(String(1024))
    line_number: Mapped[int] = mapped_column(Integer, default=0)
    end_line: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str] = mapped_column(String(50), default="")

    rule_id: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20))  # critical, high, medium, low, info
    category: Mapped[str] = mapped_column(String(100))  # secret, injection, ssrf, xss, etc.
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(Text, default="")  # The matched code snippet
    recommendation: Mapped[str] = mapped_column(Text, default="")

    analysis: Mapped["GithubAnalysis"] = relationship("GithubAnalysis", back_populates="findings")


# ── Assessment ──────────────────────────────────────────────────────────────

class Assessment(Base):
    """An assessment combining web recon, repo analysis, or both."""
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    assessment_type: Mapped[str] = mapped_column(String(50))  # WEB_RECON, REPOSITORY_SCAN, FULL_ASSESSMENT
    status: Mapped[str] = mapped_column(String(50), default="queued")  # queued, running, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Input fields
    target_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    repo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    pat: Mapped[str | None] = mapped_column(String(255), nullable=True)
    branch: Mapped[str] = mapped_column(String(255), default="main")

    # Linked results
    crawl_id: Mapped[int | None] = mapped_column(ForeignKey("crawl_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    analysis_id: Mapped[int | None] = mapped_column(ForeignKey("github_analyses.id", ondelete="SET NULL"), nullable=True, index=True)

    # Correlation stats
    correlated_endpoints: Mapped[int] = mapped_column(default=0)
    source_mappings: Mapped[int] = mapped_column(default=0)
    correlation_findings: Mapped[int] = mapped_column(default=0)

    # Timing
    created_at: Mapped[datetime.datetime] = mapped_column(default=lambda: datetime.datetime.now(tz.utc))
    started_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)

    correlations: Mapped[list["Correlation"]] = relationship("Correlation", back_populates="assessment", cascade="all, delete-orphan")


class Correlation(Base):
    """A correlation between an endpoint and a source file/finding."""
    __tablename__ = "correlations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)

    endpoint_id: Mapped[int | None] = mapped_column(ForeignKey("endpoints.id", ondelete="SET NULL"), nullable=True)
    endpoint_url: Mapped[str] = mapped_column(String(2048), default="")

    source_file: Mapped[str] = mapped_column(String(1024), default="")
    confidence: Mapped[int] = mapped_column(default=0)  # 0-100
    confidence_label: Mapped[str] = mapped_column(String(20), default="low")  # low, medium, high, very_high

    # Optional linked finding
    finding_id: Mapped[int | None] = mapped_column(ForeignKey("github_findings.id", ondelete="SET NULL"), nullable=True)
    finding_title: Mapped[str] = mapped_column(String(255), default="")
    finding_severity: Mapped[str] = mapped_column(String(20), default="")

    created_at: Mapped[datetime.datetime] = mapped_column(default=lambda: datetime.datetime.now(tz.utc))

    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="correlations")
    evidence_items: Mapped[list["CorrelationEvidence"]] = relationship("CorrelationEvidence", back_populates="correlation", cascade="all, delete-orphan")


class CorrelationEvidence(Base):
    """Individual evidence item supporting a correlation score."""
    __tablename__ = "correlation_evidence"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    correlation_id: Mapped[int] = mapped_column(ForeignKey("correlations.id", ondelete="CASCADE"), index=True)

    signal_type: Mapped[str] = mapped_column(String(100))  # exact_route, method_match, param_match, etc.
    description: Mapped[str] = mapped_column(Text, default="")
    weight: Mapped[int] = mapped_column(default=0)
    matched: Mapped[bool] = mapped_column(Boolean, default=False)

    correlation: Mapped["Correlation"] = relationship("Correlation", back_populates="evidence_items")
