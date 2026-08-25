"""
route_matcher.py — Matches discovered web endpoints against repository source code.

Uses multiple signals:
  - Exact route reference in code
  - Framework route declarations (Flask, FastAPI, Django, Express, etc.)
  - HTTP method matching
  - Parameter matching
  - Path/file naming heuristics
"""

import re
import os
from urllib.parse import urlparse


# Framework route decorators/patterns
FRAMEWORK_ROUTE_PATTERNS = [
    # Python: Flask, FastAPI, Django
    re.compile(r'@(?:app|router)\.(get|post|put|delete|patch|route)\s*\(\s*["\']([^"\']+)["\']', re.I),
    # Python: Django url patterns
    re.compile(r'path\s*\(\s*["\']([^"\']+)["\']', re.I),
    re.compile(r'url\s*\(\s*r?["\']([^"\']+)["\']', re.I),
    # JavaScript: Express, Koa, Hapi
    re.compile(r'(?:app|router|server)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', re.I),
    # JavaScript: Next.js, Nuxt
    re.compile(r'(?:get|post|put|delete|patch)ServerSideProps|definePageMeta', re.I),
    # Go: Gin, Echo, Chi
    re.compile(r'(?:GET|POST|PUT|DELETE|PATCH)\s*\(\s*"([^"]+)"', re.I),
    # PHP: Laravel, Symfony
    re.compile(r'(?:Route::|->)(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', re.I),
    # Ruby: Rails
    re.compile(r'(?:get|post|put|delete|patch|match)\s+["\']([^"\']+)["\']', re.I),
]


def normalize_path(path: str) -> str:
    """Normalize a URL path for comparison."""
    path = path.strip().rstrip("/")
    # Remove trailing .php, .aspx, .html extensions for comparison
    path = re.sub(r'\.(php|aspx|html|htm)$', '', path, flags=re.I)
    return path.lower()


def extract_path_from_url(url: str) -> str:
    """Extract the path component from a full URL."""
    try:
        parsed = urlparse(url)
        return normalize_path(parsed.path)
    except Exception:
        return normalize_path(url)


def match_exact_route(endpoint_path: str, source_content: str) -> bool:
    """Check if the endpoint path appears literally in source code."""
    # Try various quote styles
    escaped = re.escape(endpoint_path)
    patterns = [
        f'["\']/{escaped.lstrip("/")}["\']',
        f'["\']{escaped}["\']',
        f'["\']/{escaped.lstrip("/")}/?["\']',
    ]
    for p in patterns:
        if re.search(p, source_content, re.I):
            return True
    return False


def match_framework_route(endpoint_path: str, source_content: str) -> list[dict]:
    """Find framework route declarations matching the endpoint path."""
    matches = []
    norm_endpoint = normalize_path(endpoint_path)

    for pattern in FRAMEWORK_ROUTE_PATTERNS:
        for m in pattern.finditer(source_content):
            groups = m.groups()
            method = None
            route_path = None

            if len(groups) == 2:
                method, route_path = groups
            elif len(groups) == 1:
                route_path = groups[0]

            if route_path:
                norm_route = normalize_path(route_path)
                # Check for exact match or parameterized match
                if norm_route == norm_endpoint or _param_match(norm_endpoint, norm_route):
                    matches.append({
                        "method": method.upper() if method else None,
                        "route": route_path,
                        "pattern": pattern.pattern[:50],
                    })
    return matches


def _param_match(endpoint_path: str, route_path: str) -> bool:
    """Check if paths match allowing for route parameters."""
    # Convert route params to placeholders: :id -> <param>, {id} -> <param>
    route_normalized = re.sub(r'<[^>]+>', ':param', route_path)
    route_normalized = re.sub(r'\{[^}]+\}', ':param', route_normalized)
    route_normalized = re.sub(r':[a-zA-Z_]\w*', ':param', route_normalized)

    ep_normalized = endpoint_path

    # If both have the same structure after param normalization
    if route_normalized == ep_normalized:
        return True

    # Check segment count match
    route_segments = [s for s in route_normalized.split("/") if s]
    ep_segments = [s for s in ep_normalized.split("/") if s]

    if len(route_segments) != len(ep_segments):
        return False

    for rs, es in zip(route_segments, ep_segments):
        if rs != ":param" and rs != es:
            return False

    return True


def match_method(endpoint_methods: str, source_methods: list[str]) -> bool:
    """Check if any endpoint method matches source code methods."""
    ep_methods = [m.strip().upper() for m in endpoint_methods.split(",")]
    for sm in source_methods:
        if sm and sm.upper() in ep_methods:
            return True
    return False


def match_params(endpoint_params: str | None, source_content: str) -> bool:
    """Check if endpoint parameters appear in source code."""
    if not endpoint_params:
        return False
    try:
        import json
        params = json.loads(endpoint_params) if isinstance(endpoint_params, str) else endpoint_params
        if isinstance(params, list):
            for p in params:
                name = p.get("name", "") if isinstance(p, dict) else str(p)
                if name and re.search(rf'["\']?{re.escape(name)}["\']?\s*[=:]', source_content):
                    return True
        elif isinstance(params, dict):
            for name in params:
                if name and re.search(rf'["\']?{re.escape(name)}["\']?\s*[=:]', source_content):
                    return True
    except Exception:
        pass
    return False


def infer_source_file(endpoint_path: str, file_paths: list[str]) -> list[str]:
    """Suggest likely source files based on path/file naming heuristics."""
    suggestions = []
    segments = [s.lower() for s in endpoint_path.strip("/").split("/") if s and s != "api"]

    for fpath in file_paths:
        fname_lower = os.path.basename(fpath).lower()
        fname_no_ext = os.path.splitext(fname_lower)[0]

        # Direct name match: /api/users -> users.py, users.js
        for seg in segments:
            if seg == fname_no_ext or seg + "s" == fname_no_ext or seg == fname_no_ext + "s":
                suggestions.append(fpath)
                break

        # Controller/route pattern: users -> controllers/users.js, routes/users.py
        if any(x in fpath.lower() for x in ["route", "controller", "view", "handler", "endpoint"]):
            for seg in segments:
                if seg in fname_lower:
                    suggestions.append(fpath)
                    break

    return suggestions
