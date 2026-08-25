"""
form_parser.py — Extract forms from HTML and generate endpoint info.
Parses HTML forms to identify parameters, methods, and action URLs.
"""

import re
import logging
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class FormInfo:
    """Represents a discovered HTML form."""
    action: str
    method: str  # GET or POST
    inputs: List[Dict[str, str]] = field(default_factory=list)
    form_id: str = ""
    form_name: str = ""

    @property
    def parameter_names(self) -> List[str]:
        return [inp.get("name", "") for inp in self.inputs if inp.get("name")]

    @property
    def parameter_details(self) -> str:
        """Human-readable parameter list."""
        parts = []
        for inp in self.inputs:
            name = inp.get("name", "")
            if not name:
                continue
            inp_type = inp.get("type", "text")
            parts.append(f"{name} ({inp_type})")
        return ", ".join(parts) if parts else "none"


def extract_forms(html: str, page_url: str) -> List[FormInfo]:
    """
    Parse HTML and extract all form elements with their inputs.

    Returns a list of FormInfo objects with:
    - action URL (resolved to absolute)
    - method (GET/POST)
    - input fields (name, type, value)
    """
    soup = BeautifulSoup(html, "html.parser")
    forms = []

    for form_tag in soup.find_all("form"):
        action = form_tag.get("action", "")
        if action:
            action = urljoin(page_url, action)
        else:
            action = page_url

        method = (form_tag.get("method") or "GET").upper()
        form_id = form_tag.get("id", "")
        form_name = form_tag.get("name", "")

        inputs = []
        # Regular inputs
        for inp in form_tag.find_all(["input", "textarea", "select"]):
            name = inp.get("name", "")
            if not name:
                continue
            inp_type = inp.get("type", "text")
            value = inp.get("value", "")
            inputs.append({
                "name": name,
                "type": inp_type,
                "value": value,
                "tag": inp.name,
            })

        # Hidden inputs (important for pentesting — tokens, CSRF, etc.)
        for hidden in form_tag.find_all("input", type="hidden"):
            name = hidden.get("name", "")
            if name and not any(i["name"] == name for i in inputs):
                inputs.append({
                    "name": name,
                    "type": "hidden",
                    "value": hidden.get("value", ""),
                    "tag": "input",
                })

        forms.append(FormInfo(
            action=action,
            method=method,
            inputs=inputs,
            form_id=form_id,
            form_name=form_name,
        ))

    return forms


def extract_links(html: str, page_url: str) -> List[str]:
    """
    Extract all links from HTML (anchors, imports, scripts, etc.).
    Returns list of absolute URLs on the same domain.
    """
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(page_url).netloc
    links = set()

    # <a href="...">
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        try:
            full = urljoin(page_url, href).split("#")[0].split("?")[0]
            if urlparse(full).netloc == base_domain and full.startswith("http"):
                links.add(full)
        except Exception:
            pass

    # <link rel="stylesheet" href="...">
    # <script src="...">
    # <img src="...">
    # These help discover static asset paths
    for tag in soup.find_all(["link", "script", "img"], src=True):
        try:
            full = urljoin(page_url, tag["src"]).split("#")[0]
            if urlparse(full).netloc == base_domain and full.startswith("http"):
                links.add(full)
        except Exception:
            pass

    for tag in soup.find_all("link", href=True):
        try:
            full = urljoin(page_url, tag["href"]).split("#")[0]
            if urlparse(full).netloc == base_domain and full.startswith("http"):
                links.add(full)
        except Exception:
            pass

    return sorted(links)


def extract_js_endpoints(html: str, page_url: str) -> List[str]:
    """
    Extract API-like endpoints referenced in inline JavaScript.
    Looks for fetch(), axios, $.ajax, XMLHttpRequest, etc.
    """
    base_domain = urlparse(page_url).netloc
    endpoints = set()

    # Patterns for JS API calls
    patterns = [
        # fetch("/api/...") or fetch('...')
        r'fetch\s*\(\s*["\']([^"\']+)["\']',
        # $.get("/api/...") or $.post(...)
        r'\$\.(?:get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
        # axios.get("/api/...")
        r'axios\.(?:get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
        # XMLHttpRequest
        r'\.open\s*\(\s*["\'](?:GET|POST|PUT|DELETE)["\']\s*,\s*["\']([^"\']+)["\']',
        # URL strings in JS
        r'["\'](/api/[^"\']+)["\']',
        r'["\'](/v[0-9]+/[^"\']+)["\']',
        r'["\'](/graphql[^"\']*)["\']',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, html, re.IGNORECASE):
            path = match.group(1)
            if path.startswith("/"):
                full = f"{urlparse(page_url).scheme}://{base_domain}{path}"
            elif path.startswith("http"):
                full = path
            else:
                continue
            endpoints.add(full)

    return sorted(endpoints)


def extract_endpoints_from_js(js_content: str, page_url: str) -> List[str]:
    """
    Extract endpoint URLs from external JavaScript files.
    Looks for URL patterns, API paths, route definitions.
    """
    base_domain = urlparse(page_url).netloc
    endpoints = set()

    patterns = [
        # String literals that look like API paths
        r'["\'](/[a-zA-Z0-9_\-/.]+(?:\?[^"\']*)?)["\']',
        # Full URLs
        r'["\']https?://[^\s"\'<>]+["\']',
        # Template literals with paths
        r'`(/[a-zA-Z0-9_\-/.]+(?:\$\{[^}]+\}[a-zA-Z0-9_\-/.]*)*)`',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, js_content):
            path = match.group(1) if match.lastindex else match.group(0)
            path = path.strip("'\"")

            if path.startswith("/"):
                full = f"{urlparse(page_url).scheme}://{base_domain}{path}"
            elif path.startswith("http") and base_domain in path:
                full = path
            else:
                continue

            # Filter out common non-endpoint files
            skip_ext = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
                       '.woff', '.woff2', '.ttf', '.eot', '.css')
            parsed = urlparse(full)
            if any(parsed.path.lower().endswith(ext) for ext in skip_ext):
                continue

            endpoints.add(full)

    return sorted(endpoints)
