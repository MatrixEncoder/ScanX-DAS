"""
path_generator.py — Automated Attack Path Generation.

Chains correlated endpoint findings into step-by-step attack paths.
Novel method: links runtime endpoint discovery with static repository analysis
to produce prioritized, actionable attack chains.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}

# Patterns that indicate auth-gated endpoints
AUTH_PATTERNS = [
    r"/login", r"/signin", r"/auth", r"/register", r"/signup",
    r"/token", r"/session", r"/oauth", r"/callback",
]

# Patterns that indicate sensitive/admin endpoints
SENSITIVE_PATTERNS = [
    r"/admin", r"/dashboard", r"/settings", r"/config",
    r"/user", r"/account", r"/profile", r"/me",
    r"/api/internal", r"/debug", r"/health",
]

# Finding categories that chain well
CHAINABLE_FINDINGS = {
    "injection": {
        "next_step": "Data exfiltration via injected query",
        "suggestion": "Test with UNION-based or time-based blind injection",
        "chain_weight": 4,
    },
    "secret": {
        "next_step": "Use leaked credential to access protected endpoints",
        "suggestion": "Test discovered API keys/tokens against related endpoints",
        "chain_weight": 5,
    },
    "xss": {
        "next_step": "Session hijacking or credential theft via reflected/stored XSS",
        "suggestion": "Inject payload in identified parameter, test on authenticated routes",
        "chain_weight": 3,
    },
    "ssrf": {
        "next_step": "Access internal services via SSRF",
        "suggestion": "Probe internal endpoints discovered in source code (127.0.0.1, localhost)",
        "chain_weight": 4,
    },
    "redirect": {
        "next_step": "OAuth token theft or phishing via open redirect",
        "suggestion": "Chain with login endpoint to steal authorization codes",
        "chain_weight": 3,
    },
    "config": {
        "next_step": "Exploit misconfiguration for privilege escalation",
        "suggestion": "Check for debug endpoints, exposed admin panels, CORS bypass",
        "chain_weight": 2,
    },
}


@dataclass
class AttackPathStep:
    """A single step in an attack path."""
    step_order: int
    endpoint_url: str
    endpoint_id: int
    finding_title: str
    finding_severity: str
    finding_category: str
    source_file: str
    confidence: int
    action: str
    suggestion: str


@dataclass
class AttackPath:
    """A complete attack path chaining multiple endpoints and findings."""
    path_id: int
    risk_score: int
    risk_label: str
    title: str
    description: str
    steps: list[AttackPathStep] = field(default_factory=list)
    entry_point: str = ""
    impact: str = ""


class AttackPathGenerator:
    """
    Generates attack paths by chaining correlated endpoint findings.

    Novel method: Uses correlation data (endpoint <-> source file <-> finding)
    to build a directed attack graph, then extracts highest-risk paths.
    """

    def __init__(self, correlations: list, endpoints: list, findings: list):
        self.correlations = correlations
        self.endpoints = endpoints
        self.findings = findings
        self._finding_map = {f.id: f for f in findings} if findings else {}
        self._endpoint_map = {}
        for ep in endpoints:
            eid = ep.id if hasattr(ep, "id") else ep.get("id", 0)
            self._endpoint_map[eid] = ep

    def generate(self) -> list[AttackPath]:
        """Generate all viable attack paths, sorted by risk."""
        paths = []

        # Build endpoint -> findings mapping from correlations
        ep_findings = self._build_endpoint_finding_map()

        # Strategy 1: Auth bypass chains (login -> sensitive endpoint)
        auth_paths = self._gen_auth_chains(ep_findings)
        paths.extend(auth_paths)

        # Strategy 2: Finding chains (vuln at endpoint A enables exploit at endpoint B)
        finding_chains = self._gen_finding_chains(ep_findings)
        paths.extend(finding_chains)

        # Strategy 3: Single-endpoint high-risk paths (standalone critical findings)
        standalone = self._gen_standalone_paths(ep_findings)
        paths.extend(standalone)

        # Deduplicate and rank
        paths = self._deduplicate(paths)
        paths.sort(key=lambda p: p.risk_score, reverse=True)

        logger.info(f"[AttackPath] Generated {len(paths)} attack paths")
        return paths

    def _build_endpoint_finding_map(self) -> dict:
        """Map endpoint IDs to their correlated findings."""
        ep_findings = {}
        for corr in self.correlations:
            ep_id = corr.endpoint_id if hasattr(corr, "endpoint_id") else corr.get("endpoint_id")
            finding_id = corr.finding_id if hasattr(corr, "finding_id") else corr.get("finding_id")
            source_file = corr.source_file if hasattr(corr, "source_file") else corr.get("source_file", "")
            confidence = corr.confidence if hasattr(corr, "confidence") else corr.get("confidence", 0)

            if not ep_id or not finding_id:
                continue

            finding = self._finding_map.get(finding_id)
            if not finding:
                continue

            if ep_id not in ep_findings:
                ep_findings[ep_id] = []

            ep_findings[ep_id].append({
                "finding": finding,
                "source_file": source_file,
                "confidence": confidence,
            })

        return ep_findings

    def _gen_auth_chains(self, ep_findings: dict) -> list[AttackPath]:
        """Generate chains: credential theft -> protected endpoint access."""
        paths = []

        # Find login/auth endpoints
        auth_eps = []
        sensitive_eps = []
        for ep_id, ep in self._endpoint_map.items():
            url = ep.url if hasattr(ep, "url") else ep.get("url", "")
            url_lower = url.lower()

            if any(re.search(p, url_lower) for p in AUTH_PATTERNS):
                auth_eps.append((ep_id, url))
            if any(re.search(p, url_lower) for p in SENSITIVE_PATTERNS):
                sensitive_eps.append((ep_id, url))

        # Find findings on auth endpoints (credential leaks, injection)
        for auth_ep_id, auth_url in auth_eps:
            auth_findings = ep_findings.get(auth_ep_id, [])
            for af in auth_findings:
                finding = af["finding"]
                category = finding.category if hasattr(finding, "category") else finding.get("category", "")
                severity = finding.severity if hasattr(finding, "severity") else finding.get("severity", "")
                title = finding.title if hasattr(finding, "title") else finding.get("title", "")

                if category not in CHAINABLE_FINDINGS:
                    continue

                chain_info = CHAINABLE_FINDINGS[category]

                # Build path: auth exploit -> sensitive endpoint
                steps = [AttackPathStep(
                    step_order=1,
                    endpoint_url=auth_url,
                    endpoint_id=auth_ep_id,
                    finding_title=title,
                    finding_severity=severity,
                    finding_category=category,
                    source_file=af["source_file"],
                    confidence=af["confidence"],
                    action=f"Exploit {category} on authentication endpoint",
                    suggestion=chain_info["suggestion"],
                )]

                for sens_ep_id, sens_url in sensitive_eps[:3]:
                    steps.append(AttackPathStep(
                        step_order=2,
                        endpoint_url=sens_url,
                        endpoint_id=sens_ep_id,
                        finding_title="Protected endpoint accessible post-auth",
                        finding_severity="high",
                        finding_category="auth_chain",
                        source_file="",
                        confidence=60,
                        action="Access protected endpoint with stolen credentials",
                        suggestion="Use extracted session token or credentials to access this endpoint",
                    ))

                risk = self._calc_risk(steps)
                paths.append(AttackPath(
                    path_id=0,
                    risk_score=risk,
                    risk_label=self._risk_label(risk),
                    title=f"Auth Bypass: {title} -> Protected Endpoints",
                    description=f"Exploit {category} on {auth_url} to gain access to {len(sensitive_eps)} protected endpoint(s)",
                    steps=steps,
                    entry_point=auth_url,
                    impact="Full account takeover or admin access",
                ))

        return paths

    def _gen_finding_chains(self, ep_findings: dict) -> list[AttackPath]:
        """Generate chains where one finding enables another endpoint exploit."""
        paths = []

        # Group findings by category
        category_eps = {}
        for ep_id, findings_list in ep_findings.items():
            for fi in findings_list:
                finding = fi["finding"]
                category = finding.category if hasattr(finding, "category") else finding.get("category", "")
                if category not in category_eps:
                    category_eps[category] = []
                ep_obj = self._endpoint_map.get(ep_id)
                url = ep_obj.url if hasattr(ep_obj, "url") else ep_obj.get("url", "") if ep_obj else ""
                category_eps[category].append({
                    "ep_id": ep_id,
                    "url": url,
                    "finding": finding,
                    "source_file": fi["source_file"],
                    "confidence": fi["confidence"],
                })

        # SSRF chains: SSRF endpoint -> internal endpoints
        if "ssrf" in category_eps:
            for ssrf_entry in category_eps["ssrf"]:
                steps = [AttackPathStep(
                    step_order=1,
                    endpoint_url=ssrf_entry["url"],
                    endpoint_id=ssrf_entry["ep_id"],
                    finding_title=ssrf_entry["finding"].title if hasattr(ssrf_entry["finding"], "title") else ssrf_entry["finding"].get("title", ""),
                    finding_severity=ssrf_entry["finding"].severity if hasattr(ssrf_entry["finding"], "severity") else ssrf_entry["finding"].get("severity", ""),
                    finding_category="ssrf",
                    source_file=ssrf_entry["source_file"],
                    confidence=ssrf_entry["confidence"],
                    action="Trigger SSRF to access internal services",
                    suggestion="Inject internal URLs (127.0.0.1, localhost, 169.254.169.254) into the vulnerable parameter",
                )]

                # Find other endpoints that could be SSRF targets
                for other_ep_id, other_findings in ep_findings.items():
                    if other_ep_id == ssrf_entry["ep_id"]:
                        continue
                    other_ep = self._endpoint_map.get(other_ep_id)
                    other_url = other_ep.url if hasattr(other_ep, "url") else other_ep.get("url", "") if other_ep else ""
                    if "internal" in other_url.lower() or "127.0.0.1" in other_url or "admin" in other_url.lower():
                        steps.append(AttackPathStep(
                            step_order=2,
                            endpoint_url=other_url,
                            endpoint_id=other_ep_id,
                            finding_title="Internal endpoint reachable via SSRF",
                            finding_severity="critical",
                            finding_category="ssrf_target",
                            source_file="",
                            confidence=50,
                            action="Access internal endpoint via SSRF",
                            suggestion="Route request through the SSRF vulnerability to reach this internal endpoint",
                        ))

                if len(steps) > 1:
                    risk = self._calc_risk(steps)
                    paths.append(AttackPath(
                        path_id=0,
                        risk_score=risk,
                        risk_label=self._risk_label(risk),
                        title=f"SSRF Chain: {ssrf_entry['url']} -> Internal Services",
                        description=f"Use SSRF vulnerability to pivot to {len(steps) - 1} internal endpoint(s)",
                        steps=steps,
                        entry_point=ssrf_entry["url"],
                        impact="Internal network access, sensitive data exfiltration",
                    ))

        # Secret leak chains: leaked key -> API endpoint access
        if "secret" in category_eps:
            for secret_entry in category_eps["secret"]:
                steps = [AttackPathStep(
                    step_order=1,
                    endpoint_url=secret_entry["url"],
                    endpoint_id=secret_entry["ep_id"],
                    finding_title=secret_entry["finding"].title if hasattr(secret_entry["finding"], "title") else secret_entry["finding"].get("title", ""),
                    finding_severity=secret_entry["finding"].severity if hasattr(secret_entry["finding"], "severity") else secret_entry["finding"].get("severity", ""),
                    finding_category="secret",
                    source_file=secret_entry["source_file"],
                    confidence=secret_entry["confidence"],
                    action="Extract leaked credential from source code",
                    suggestion="Locate the hardcoded secret and use it for authentication",
                )]

                # Find API endpoints that could use this credential
                api_count = 0
                for other_ep_id, other_findings in ep_findings.items():
                    if other_ep_id == secret_entry["ep_id"]:
                        continue
                    other_ep = self._endpoint_map.get(other_ep_id)
                    other_url = other_ep.url if hasattr(other_ep, "url") else other_ep.get("url", "") if other_ep else ""
                    is_api = other_ep.is_api if hasattr(other_ep, "is_api") else other_ep.get("is_api", False) if other_ep else False
                    if is_api or "/api/" in other_url:
                        api_count += 1
                        if api_count <= 3:
                            steps.append(AttackPathStep(
                                step_order=len(steps) + 1,
                                endpoint_url=other_url,
                                endpoint_id=other_ep_id,
                                finding_title="API endpoint accessible with leaked credential",
                                finding_severity="high",
                                finding_category="secret_chain",
                                source_file="",
                                confidence=40,
                                action="Authenticate to API endpoint using leaked credential",
                                suggestion="Test the extracted API key/token against this endpoint",
                            ))

                if len(steps) > 1:
                    risk = self._calc_risk(steps)
                    paths.append(AttackPath(
                        path_id=0,
                        risk_score=risk,
                        risk_label=self._risk_label(risk),
                        title=f"Secret Leak Chain: {secret_entry['finding'].title if hasattr(secret_entry['finding'], 'title') else secret_entry['finding'].get('title', '')}",
                        description=f"Use leaked credential to access {api_count} API endpoint(s)",
                        steps=steps,
                        entry_point=secret_entry["url"],
                        impact="Unauthorized API access, data breach",
                    ))

        return paths

    def _gen_standalone_paths(self, ep_findings: dict) -> list[AttackPath]:
        """Generate standalone paths for high-severity single findings."""
        paths = []

        for ep_id, findings_list in ep_findings.items():
            for fi in findings_list:
                finding = fi["finding"]
                severity = finding.severity if hasattr(finding, "severity") else finding.get("severity", "")
                category = finding.category if hasattr(finding, "category") else finding.get("category", "")
                title = finding.title if hasattr(finding, "title") else finding.get("title", "")

                if severity not in ("critical", "high"):
                    continue
                if category not in CHAINABLE_FINDINGS:
                    continue

                chain_info = CHAINABLE_FINDINGS[category]
                ep_obj = self._endpoint_map.get(ep_id)
                url = ep_obj.url if hasattr(ep_obj, "url") else ep_obj.get("url", "") if ep_obj else ""

                step = AttackPathStep(
                    step_order=1,
                    endpoint_url=url,
                    endpoint_id=ep_id,
                    finding_title=title,
                    finding_severity=severity,
                    finding_category=category,
                    source_file=fi["source_file"],
                    confidence=fi["confidence"],
                    action=f"Exploit {category} vulnerability",
                    suggestion=chain_info["suggestion"],
                )

                risk = self._calc_risk([step])
                paths.append(AttackPath(
                    path_id=0,
                    risk_score=risk,
                    risk_label=self._risk_label(risk),
                    title=f"{severity.upper()}: {title}",
                    description=f"Standalone {category} vulnerability at {url}",
                    steps=[step],
                    entry_point=url,
                    impact=chain_info["next_step"],
                ))

        return paths

    def _calc_risk(self, steps: list[AttackPathStep]) -> int:
        """Calculate path risk score (0-100)."""
        if not steps:
            return 0

        severity_scores = {"critical": 35, "high": 25, "medium": 15, "low": 5, "info": 0}
        base = sum(severity_scores.get(s.finding_severity, 0) for s in steps)
        chain_bonus = min(len(steps) * 8, 25)
        confidence_avg = sum(s.confidence for s in steps) / len(steps) if steps else 0
        conf_factor = confidence_avg / 100

        raw = (base + chain_bonus) * conf_factor
        return min(int(raw), 100)

    @staticmethod
    def _risk_label(score: int) -> str:
        if score >= 75:
            return "critical"
        if score >= 50:
            return "high"
        if score >= 25:
            return "medium"
        return "low"

    def _deduplicate(self, paths: list[AttackPath]) -> list[AttackPath]:
        """Remove duplicate paths based on entry point + first finding."""
        seen = set()
        unique = []
        for p in paths:
            key = (p.entry_point, p.steps[0].finding_title if p.steps else "")
            if key not in seen:
                seen.add(key)
                unique.append(p)
        return unique
