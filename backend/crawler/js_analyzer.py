"""
js_analyzer.py — Analyze JavaScript files and inline scripts for endpoint discovery.
Extracts API URLs, route definitions, and hidden paths from JS code.
"""

import re
import logging
from urllib.parse import urljoin, urlparse
from typing import List

import requests

logger = logging.getLogger(__name__)

# Suppress InsecureRequestWarning
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)


def analyze_inline_scripts(html: str, page_url: str) -> List[str]:
    """Extract endpoints from inline <script> blocks in HTML."""
    from backend.crawler.form_parser import extract_js_endpoints
    return extract_js_endpoints(html, page_url)


def analyze_external_js(js_urls: List[str], base_url: str) -> List[str]:
    """
    Download and analyze external JavaScript files for endpoint URLs.
    Returns discovered endpoint paths.
    """
    base_domain = urlparse(base_url).netloc
    discovered = set()

    for js_url in js_urls[:20]:  # Limit to prevent excessive requests
        try:
            resp = requests.get(
                js_url,
                timeout=10,
                verify=False,
                headers={"User-Agent": "ScanX-Crawler/1.0"},
            )
            if resp.status_code == 200 and "javascript" in resp.headers.get("content-type", ""):
                endpoints = _extract_from_js_source(resp.text, base_domain)
                discovered.update(endpoints)
        except Exception as e:
            logger.debug(f"[JS] Failed to fetch {js_url}: {e}")

    return sorted(discovered)


def extract_js_urls(html: str, page_url: str) -> List[str]:
    """Extract external JavaScript file URLs from HTML."""
    urls = []
    patterns = [
        r'<script[^>]+src=["\']([^"\']+)["\']',
        r'import\s+.*?from\s+["\']([^"\']+)["\']',
        r'import\s+["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, html):
            src = match.group(1)
            full = urljoin(page_url, src)
            if full.startswith("http"):
                urls.append(full)
    return list(set(urls))


def _extract_from_js_source(js_code: str, base_domain: str) -> set:
    """Extract API-like endpoint paths from JavaScript source code."""
    endpoints = set()

    patterns = [
        # fetch / axios / $.ajax paths
        r'(?:fetch|axios\.(?:get|post|put|delete|patch))\s*\(\s*["\']([^"\']+)["\']',
        r'\$\.(?:get|post|put|delete)\s*\(\s*["\']([^"\']+)["\']',
        # $.ajax({ url: "..." })
        r'url\s*:\s*["\']([^"\']+)["\']',
        # open(method, url)
        r'\.open\s*\(\s*["\'][A-Z]+["\']\s*,\s*["\']([^"\']+)["\']',
        # String paths that look like API routes
        r'["\'](/api/[a-zA-Z0-9_\-/.]+(?:\?[^"\']*)?)["\']',
        r'["\'](/v[0-9]+/[a-zA-Z0-9_\-/.]+(?:\?[^"\']*)?)["\']',
        # Route definitions (React Router, Vue Router, etc.)
        r'path\s*:\s*["\'](/[^"\']+)["\']',
        r'route\s*\(\s*["\']([^"\']+)["\']',
        # URL concatenation patterns
        r'(?:baseURL|apiUrl|apiBase)\s*[=+]\s*["\']([^"\']+)["\']',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, js_code, re.IGNORECASE):
            path = match.group(1)
            if not path:
                continue

            if path.startswith("/"):
                full = f"https://{base_domain}{path}"
            elif path.startswith("http") and base_domain in path:
                full = path
            else:
                continue

            # Skip static assets
            parsed = urlparse(full)
            skip_ext = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
                       '.woff', '.woff2', '.ttf', '.eot', '.css', '.map')
            if any(parsed.path.lower().endswith(ext) for ext in skip_ext):
                continue

            endpoints.add(full)

    return endpoints
