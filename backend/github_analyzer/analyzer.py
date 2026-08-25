"""
analyzer.py — GitHub repository security analyzer.

Orchestrates the full pipeline:
  1. Fetch files from GitHub
  2. Run security rules against each file
  3. Return structured findings
"""

import logging
import re
import time
from typing import List, Optional
from dataclasses import dataclass, field

from backend.github_analyzer.github_client import GithubClient, RepoFile, parse_github_url
from backend.github_analyzer.security_rules import ALL_RULES, Rule

logger = logging.getLogger(__name__)


@dataclass
class Finding:
    """A detected security finding."""
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


@dataclass
class AnalysisResult:
    """Complete analysis result."""
    repo_url: str
    repo_name: str
    branch: str
    files_analyzed: int = 0
    total_files: int = 0
    findings: List[Finding] = field(default_factory=list)
    duration: float = 0.0
    errors: List[str] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "medium")

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "low")

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "info")


class RepoAnalyzer:
    """
    Analyze a GitHub repository for security vulnerabilities.
    Fetches files via GitHub API and scans with pattern-based rules.
    """

    def __init__(self, token: Optional[str] = None):
        self.client = GithubClient(token=token)

    def analyze(self, repo_url: str, branch: str = "main") -> AnalysisResult:
        """Run full security analysis on a repository."""
        start = time.time()
        owner, repo_name = parse_github_url(repo_url)
        full_name = f"{owner}/{repo_name}"

        result = AnalysisResult(
            repo_url=repo_url,
            repo_name=full_name,
            branch=branch,
        )

        # Fetch files — try API first, fall back to git clone
        logger.info(f"[Analyzer] Fetching files from {full_name} ({branch})...")
        try:
            files = self.client.fetch_repo_files(owner, repo_name, branch=branch)
            if not files:
                raise RuntimeError("API returned 0 files — may be rate limited")
        except Exception as api_err:
            logger.warning(f"[Analyzer] API fetch failed ({api_err}), trying git clone...")
            try:
                files = self.client.fetch_repo_via_clone(repo_url, branch=branch)
            except Exception as clone_err:
                logger.error(f"[Analyzer] Clone also failed: {clone_err}")
                result.errors.append(f"API: {api_err} | Clone: {clone_err}")
                result.duration = time.time() - start
                return result

        result.total_files = len(files)
        result.files_analyzed = len(files)
        logger.info(f"[Analyzer] Scanning {len(files)} files...")

        # Scan each file
        for file in files:
            findings = self._scan_file(file)
            result.findings.extend(findings)

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        result.findings.sort(key=lambda f: (severity_order.get(f.severity, 99), f.file_path))

        result.duration = round(time.time() - start, 2)
        logger.info(
            f"[Analyzer] Complete: {len(result.findings)} findings "
            f"({result.critical_count}C/{result.high_count}H/{result.medium_count}M/"
            f"{result.low_count}L/{result.info_count}I) in {result.duration}s"
        )
        return result

    def _scan_file(self, file: RepoFile) -> List[Finding]:
        """Scan a single file against all applicable rules."""
        findings = []
        if not file.content:
            return findings

        # Skip bundled/minified files
        from backend.github_analyzer.github_client import _should_skip_file
        if _should_skip_file(file.path, file.name, file.content):
            return findings

        for rule in ALL_RULES:
            # Language filter
            if rule.languages and file.language not in rule.languages:
                continue

            try:
                matches = list(re.finditer(rule.pattern, file.content, rule.flags))
            except re.error:
                continue

            for match in matches:
                # Check exclude patterns
                if rule.exclude_patterns:
                    line_start = file.content.rfind("\n", 0, match.start()) + 1
                    line_end = file.content.find("\n", match.end())
                    if line_end == -1:
                        line_end = len(file.content)
                    full_line = file.content[line_start:line_end]
                    if any(re.search(ep, full_line, re.IGNORECASE) for ep in rule.exclude_patterns):
                        continue

                # Get line number
                line_num = file.content[:match.start()].count("\n") + 1
                end_line = file.content[:match.end()].count("\n") + 1

                # Get evidence (the matched line)
                line_start = file.content.rfind("\n", 0, match.start()) + 1
                line_end = file.content.find("\n", match.end())
                if line_end == -1:
                    line_end = len(file.content)
                evidence = file.content[line_start:line_end].strip()
                # Truncate long evidence
                if len(evidence) > 200:
                    evidence = evidence[:200] + "..."

                findings.append(Finding(
                    file_path=file.path,
                    line_number=line_num,
                    end_line=end_line,
                    language=file.language,
                    rule_id=rule.id,
                    severity=rule.severity,
                    category=rule.category,
                    title=rule.title,
                    description=rule.description,
                    evidence=evidence,
                    recommendation=rule.recommendation,
                ))

        return findings
