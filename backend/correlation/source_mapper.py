"""
source_mapper.py — Maps repository files and findings to web endpoints.

Provides utilities for indexing repo files and matching findings
to endpoints based on code references.
"""

import re
import os
from dataclasses import dataclass


@dataclass
class RepoIndex:
    """Indexed repository data for correlation."""
    files: list[dict]          # [{path, content, language}]
    findings: list[dict]       # [{id, file_path, line_number, title, severity, category, evidence, description}]
    file_paths: list[str]      # Just the paths


def build_repo_index(repo_files: list, findings: list[dict] = None) -> RepoIndex:
    """
    Build an index of repository files and findings for correlation.

    Args:
        repo_files: list of RepoFile objects or dicts with path, content, language
        findings: list of finding dicts with file_path, title, severity, etc.
    """
    files = []
    file_paths = []
    for f in repo_files:
        entry = {
            "path": f.path if hasattr(f, "path") else f.get("path", ""),
            "content": f.content if hasattr(f, "content") else f.get("content", ""),
            "language": f.language if hasattr(f, "language") else f.get("language", ""),
        }
        files.append(entry)
        file_paths.append(entry["path"])

    indexed_findings = []
    for f in (findings or []):
        indexed_findings.append({
            "id": f.id if hasattr(f, "id") else f.get("id"),
            "file_path": f.file_path if hasattr(f, "file_path") else f.get("file_path", ""),
            "line_number": f.line_number if hasattr(f, "line_number") else f.get("line_number", 0),
            "title": f.title if hasattr(f, "title") else f.get("title", ""),
            "severity": f.severity if hasattr(f, "severity") else f.get("severity", ""),
            "category": f.category if hasattr(f, "category") else f.get("category", ""),
            "evidence": f.evidence if hasattr(f, "evidence") else f.get("evidence", ""),
            "description": f.description if hasattr(f, "description") else f.get("description", ""),
        })

    return RepoIndex(files=files, findings=indexed_findings, file_paths=file_paths)


def find_endpoint_references(endpoint_path: str, repo_index: RepoIndex) -> list[dict]:
    """
    Find all references to an endpoint path in the repository.

    Returns list of {file_path, line_hint, reference_type}
    """
    references = []
    norm_path = endpoint_path.strip("/").lower()

    for f in repo_index.files:
        content = f["content"]
        if not content:
            continue

        # Look for the path in quotes
        escaped = re.escape(endpoint_path)
        patterns = [
            (f'["\']/{escaped.lstrip("/")}["\']', "exact_reference"),
            (f'["\']{escaped}["\']', "exact_reference"),
            (f'["\']/{escaped.lstrip("/")}/?["\']', "exact_reference"),
        ]

        for pat, ref_type in patterns:
            for m in re.finditer(pat, content, re.I):
                line_num = content[:m.start()].count("\n") + 1
                references.append({
                    "file_path": f["path"],
                    "line_hint": line_num,
                    "reference_type": ref_type,
                })

    return references


def find_finding_references(finding: dict, repo_index: RepoIndex) -> list[dict]:
    """
    Find references to a security finding in source code.
    Looks for the rule-related patterns in files near the finding location.
    """
    refs = []
    evidence = finding.get("evidence", "")
    if not evidence:
        return refs

    # Find files that contain similar patterns to the finding evidence
    evidence_words = [w for w in re.split(r'\W+', evidence) if len(w) > 3][:5]

    for f in repo_index.files:
        if f["path"] == finding.get("file_path"):
            continue
        content = f["content"]
        if not content:
            continue

        matches = sum(1 for w in evidence_words if w in content)
        if matches >= 2:
            refs.append({
                "file_path": f["path"],
                "match_count": matches,
                "reference_type": "pattern_similarity",
            })

    return refs
