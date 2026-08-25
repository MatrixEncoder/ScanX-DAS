"""
engine.py — Correlation engine that links web endpoints to repository source code and findings.

Orchestrates:
  1. Route matching (endpoint -> source file)
  2. Finding correlation (endpoint -> vulnerability finding)
  3. Confidence scoring with evidence
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from backend.correlation.route_matcher import (
    extract_path_from_url,
    match_exact_route,
    match_framework_route,
    match_method,
    match_params,
    infer_source_file,
)
from backend.correlation.source_mapper import (
    build_repo_index,
    find_endpoint_references,
    find_finding_references,
    RepoIndex,
)
from backend.correlation.scoring import compute_score

logger = logging.getLogger(__name__)


@dataclass
class CorrelationResult:
    """A single correlation between an endpoint and source code."""
    endpoint_id: int
    endpoint_url: str
    source_file: str
    confidence: int
    confidence_label: str
    evidence: list[dict] = field(default_factory=list)
    finding_id: Optional[int] = None
    finding_title: str = ""
    finding_severity: str = ""


class CorrelationEngine:
    """
    Correlates discovered web endpoints with repository source code and findings.

    This is an optional advanced capability — it does not depend on or block
    either the web recon or repository analysis scanners.
    """

    def __init__(self, repo_index: RepoIndex):
        self.repo_index = repo_index

    def correlate(self, endpoints: list) -> list[CorrelationResult]:
        """
        Run correlation across all endpoints against the repository index.

        Args:
            endpoints: list of Endpoint model objects or dicts

        Returns:
            list of CorrelationResult, sorted by confidence descending
        """
        results = []

        for ep in endpoints:
            ep_url = ep.url if hasattr(ep, "url") else ep.get("url", "")
            ep_id = ep.id if hasattr(ep, "id") else ep.get("id", 0)
            ep_methods = ep.methods if hasattr(ep, "methods") else ep.get("methods", "GET")
            ep_params = ep.parameters if hasattr(ep, "parameters") else ep.get("parameters")

            ep_result = self._correlate_single(ep_id, ep_url, ep_methods, ep_params)
            if ep_result:
                results.append(ep_result)

        # Also check for finding-level correlations
        results = self._attach_findings(results)

        results.sort(key=lambda r: r.confidence, reverse=True)
        logger.info(f"[Correlation] Correlated {len(results)} endpoints "
                     f"({sum(1 for r in results if r.confidence >= 40)} with medium+ confidence)")
        return results

    def _correlate_single(self, ep_id: int, ep_url: str, ep_methods: str, ep_params) -> Optional[CorrelationResult]:
        """Correlate a single endpoint against the repository."""
        ep_path = extract_path_from_url(ep_url)
        if not ep_path or ep_path == "/":
            return None

        # Gather evidence from all signals
        evidence = []
        best_file = None
        best_score = 0

        # 1. Exact route reference in code
        exact_refs = find_endpoint_references(ep_url, self.repo_index)
        has_exact = len(exact_refs) > 0
        evidence.append({
            "signal_type": "exact_route_reference",
            "description": f"Found {len(exact_refs)} exact reference(s) in source code" if has_exact else "No exact route reference found in source code",
            "weight": 40,
            "matched": has_exact,
        })
        if exact_refs:
            best_file = exact_refs[0]["file_path"]

        # 2. Framework route declarations
        framework_matches = []
        for f in self.repo_index.files:
            matches = match_framework_route(ep_path, f["content"])
            for fm in matches:
                fm["file_path"] = f["path"]
                framework_matches.append(fm)

        has_framework = len(framework_matches) > 0
        evidence.append({
            "signal_type": "framework_route_match",
            "description": f"Found {len(framework_matches)} framework route declaration(s)" if has_framework else "No framework route declaration found",
            "weight": 10,
            "matched": has_framework,
        })
        if framework_matches and not best_file:
            best_file = framework_matches[0]["file_path"]

        # 3. HTTP method match
        source_methods = [fm.get("method", "") for fm in framework_matches if fm.get("method")]
        method_match = match_method(ep_methods, source_methods) if source_methods else False
        evidence.append({
            "signal_type": "method_match",
            "description": f"HTTP method {ep_methods.strip()} matches source declaration" if method_match else "HTTP method not confirmed in source",
            "weight": 20,
            "matched": method_match,
        })

        # 4. Parameter match
        param_match = False
        for f in self.repo_index.files:
            if match_params(ep_params, f["content"]):
                param_match = True
                if not best_file:
                    best_file = f["path"]
                break
        evidence.append({
            "signal_type": "param_match",
            "description": "Endpoint parameters found in source code" if param_match else "No parameter references found",
            "weight": 10,
            "matched": param_match,
        })

        # 5. File naming heuristics (weak signal)
        if not best_file:
            suggestions = infer_source_file(ep_path, self.repo_index.file_paths)
            if suggestions:
                best_file = suggestions[0]
                evidence.append({
                    "signal_type": "file_naming",
                    "description": f"File name heuristic match: {best_file}",
                    "weight": 5,
                    "matched": True,
                })

        # Compute score
        score, label = compute_score(evidence)

        # Only return results with some evidence
        if score == 0 and not best_file:
            return None

        if not best_file:
            best_file = "Unknown"

        return CorrelationResult(
            endpoint_id=ep_id,
            endpoint_url=ep_url,
            source_file=best_file,
            confidence=score,
            confidence_label=label,
            evidence=evidence,
        )

    def _attach_findings(self, results: list[CorrelationResult]) -> list[CorrelationResult]:
        """Attach relevant security findings to correlated endpoints."""
        for result in results:
            if not result.source_file or result.source_file == "Unknown":
                continue

            # Find findings in the same file or related files
            for finding in self.repo_index.findings:
                finding_file = finding.get("file_path", "")
                if not finding_file:
                    continue

                # Check if finding is in the correlated source file
                if finding_file == result.source_file:
                    result.finding_id = finding.get("id")
                    result.finding_title = finding.get("title", "")
                    result.finding_severity = finding.get("severity", "")
                    # Boost confidence slightly for having a finding
                    result.confidence = min(result.confidence + 5, 100)
                    if result.confidence >= 90:
                        result.confidence_label = "very_high"
                    elif result.confidence >= 70:
                        result.confidence_label = "high"
                    break

                # Check if finding references the endpoint path
                evidence_text = finding.get("evidence", "")
                if evidence_text and result.endpoint_url.split("//")[-1].split("?")[0] in evidence_text:
                    result.finding_id = finding.get("id")
                    result.finding_title = finding.get("title", "")
                    result.finding_severity = finding.get("severity", "")
                    result.confidence = min(result.confidence + 3, 100)
                    break

        return results
