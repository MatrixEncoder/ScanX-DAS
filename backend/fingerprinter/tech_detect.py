"""
tech_detect.py — Technology fingerprinting module.

Detects web server, programming language, framework, CMS, JS libraries,
and other technologies from HTTP headers and HTML content.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)


@dataclass
class TechMatch:
    """A detected technology."""
    name: str
    category: str   # server, language, framework, cms, js_library, analytics, etc.
    version: str = ""
    confidence: str = "High"  # High, Medium, Low
    evidence: str = ""        # What indicated this technology


@dataclass
class TechFingerprint:
    """Complete technology fingerprint for a target."""
    server: str = ""
    language: str = ""
    frameworks: List[str] = field(default_factory=list)
    cms: str = ""
    js_libraries: List[str] = field(default_factory=list)
    analytics: List[str] = field(default_factory=list)
    security_headers: Dict[str, bool] = field(default_factory=dict)
    other: List[str] = field(default_factory=list)
    all_matches: List[TechMatch] = field(default_factory=list)


# ── Detection Signatures ──────────────────────────────────────────────────

SERVER_SIGNATURES = {
    "Apache": r"Apache",
    "Nginx": r"nginx",
    "IIS": r"Microsoft-IIS",
    "LiteSpeed": r"LiteSpeed",
    "Caddy": r"Caddy",
    "OpenResty": r"openresty",
    "Cloudflare": r"cloudflare",
    "AWS ALB": r"awselb",
    "Gunicorn": r"gunicorn",
    "uvicorn": r"uvicorn",
    "Jetty": r"Jetty",
    "Tomcat": r"Apache-Coyote|Tomcat",
}

LANGUAGE_SIGNATURES = {
    "PHP": [
        (r"X-Powered-By:\s*PHP", "header"),
        (r"\.php\b", "url_pattern"),
        (r"phpinfo|phpversion", "content"),
    ],
    "Python": [
        (r"X-Powered-By:\s*Python|Server:\s*(?:gunicorn|uvicorn|waitress)", "header"),
        (r"\.py\b|wsgi|asgi", "content"),
        (r"__csrftoken|csrfmiddlewaretoken", "content"),
    ],
    "Java": [
        (r"X-Powered-By:\s*Servlet|Server:\s*(?:Apache-Coyote|Jetty)", "header"),
        (r"\.jsp|\.do\b|\.action\b|JSESSIONID", "content_or_header"),
        (r"Spring|Struts|Hibernate", "content"),
    ],
    "Ruby": [
        (r"X-Powered-By:\s*Phusion Passenger|Server:\s*(?:thin|puma|unicorn)", "header"),
        (r"\.rb|_token.*authenticity", "content"),
    ],
    "Node.js": [
        (r"X-Powered-By:\s*Express|Server:\s*(?:Express|gunicorn|uvicorn)", "header"),
        (r"__NEXT_DATA__|__NUXT__", "content"),
    ],
    ".NET": [
        (r"X-Powered-By:\s*ASP\.NET|X-AspNet-Version|X-AspNetMvc-Version", "header"),
        (r"\.(aspx|ashx|asmx)\b|__VIEWSTATE|__EVENTVALIDATION", "content"),
    ],
}

FRAMEWORK_SIGNATURES = {
    "Laravel": [r"laravel|XSRF-TOKEN|laravel_session", "content_or_header"],
    "Django": [r"csrfmiddlewaretoken|django|__admin__", "content"],
    "Flask": [r"flask|werkzeug", "content_or_header"],
    "Spring": [r"Spring|springframework|JSESSIONID", "content_or_header"],
    "Rails": [r"ruby|rails|_token", "content"],
    "Express": [r"express|x-powered-by.*express", "content_or_header"],
    "Next.js": [r"__NEXT_DATA__|_next/static", "content"],
    "Nuxt.js": [r"__NUXT__|_nuxt/", "content"],
    "Angular": [r"ng-version|angular|ng-", "content"],
    "React": [r"react|_reactroot|__REACT", "content"],
    "Vue.js": [r"vue|__vue__|v-cloak", "content"],
    "jQuery": [r"jquery", "content"],
    "Bootstrap": [r"bootstrap", "content"],
    "ASP.NET MVC": [r"__VIEWSTATE|__EVENTVALIDATION|antiforgery", "content"],
    "FastAPI": [r"fastapi|openapi\.json|/docs|/redoc", "content"],
    "WordPress": [r"wp-content|wp-includes|wordpress", "content"],
    "Drupal": [r"drupal|sites/default/files", "content"],
    "Joomla": [r"joomla|/components/|/modules/", "content"],
}

CMS_SIGNATURES = {
    "WordPress": [
        r"wp-content|wp-includes|wp-admin|wordpress",
        r"generator.*WordPress",
        r"/xmlrpc\.php",
    ],
    "Drupal": [
        r"drupal|sites/default/files|Drupal\.settings",
        r"generator.*Drupal",
    ],
    "Joomla": [
        r"joomla|/components/|/modules/|com_content",
        r"generator.*Joomla",
    ],
    "Shopify": [r"shopify|cdn\.shopify\.com"],
    "Wix": [r"wix\.com|X-Wix"],
    "Squarespace": [r"squarespace|static\.squarespace"],
}

JS_LIB_SIGNATURES = {
    "jQuery": r"jquery[/-](\d+\.\d+[\.\d]*)",
    "React": r"react[/-](\d+\.\d+[\.\d]*)|react\.production\.min\.js",
    "Vue.js": r"vue[/-](\d+\.\d+[\.\d]*)|vue\.min\.js",
    "Angular": r"angular[/-](\d+\.\d+[\.\d]*)|angular\.min\.js",
    "Bootstrap": r"bootstrap[/-](\d+\.\d+[\.\d]*)",
    "Lodash": r"lodash[/-](\d+\.\d+[\.\d]*)",
    "Axios": r"axios[/-](\d+\.\d+[\.\d]*)",
    "Moment.js": r"moment[/-](\d+\.\d+[\.\d]*)",
    "D3.js": r"d3[/-](\d+\.\d+[\.\d]*)",
    "Chart.js": r"chart\.js[/-](\d+\.\d+[\.\d]*)",
    "Font Awesome": r"font-?awesome|fontawesome",
    "Google Analytics": r"google-analytics\.com|googletagmanager\.com|gtag",
}

SECURITY_HEADERS = {
    "Content-Security-Policy": "Content-Security-Policy",
    "X-Frame-Options": "X-Frame-Options",
    "X-Content-Type-Options": "X-Content-Type-Options",
    "Strict-Transport-Security": "Strict-Transport-Security",
    "Referrer-Policy": "Referrer-Policy",
    "Permissions-Policy": "Permissions-Policy",
    "X-XSS-Protection": "X-XSS-Protection",
}


class TechFingerprinter:
    """
    Fingerprint technologies used by a web target.
    Analyzes HTTP headers, HTML content, and URL patterns.
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ScanX-Fingerprinter/1.0"})
        self.session.verify = False

    def fingerprint(self, target_url: str) -> TechFingerprint:
        """
        Perform full technology fingerprinting on a target.
        Fetches the main page and analyzes all signals.
        """
        fp = TechFingerprint()

        url = target_url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
        except Exception as e:
            logger.warning(f"[Fingerprinter] Failed to fetch {target_url}: {e}")
            return fp

        headers = {k.lower(): v for k, v in resp.headers.items()}
        body = resp.text
        body_lower = body.lower()

        # ── Server detection ──
        server_header = headers.get("server", "")
        for name, pattern in SERVER_SIGNATURES.items():
            if re.search(pattern, server_header, re.IGNORECASE):
                fp.server = name
                fp.all_matches.append(TechMatch(
                    name=name, category="server", evidence=f"Server: {server_header}"
                ))
                break

        # ── Language detection ──
        for lang, checks in LANGUAGE_SIGNATURES.items():
            for pattern, check_type in checks:
                if check_type == "header" and re.search(pattern, "\n".join(f"{k}: {v}" for k, v in headers.items()), re.IGNORECASE):
                    fp.language = lang
                    fp.all_matches.append(TechMatch(name=lang, category="language", evidence=f"Header match: {pattern}"))
                    break
                elif check_type == "content" and re.search(pattern, body, re.IGNORECASE):
                    fp.language = lang
                    fp.all_matches.append(TechMatch(name=lang, category="language", evidence=f"Content match: {pattern}"))
                    break
                elif check_type == "content_or_header" and (
                    re.search(pattern, body, re.IGNORECASE) or
                    re.search(pattern, "\n".join(f"{k}: {v}" for k, v in headers.items()), re.IGNORECASE)
                ):
                    fp.language = lang
                    fp.all_matches.append(TechMatch(name=lang, category="language", evidence=f"Match: {pattern}"))
                    break

        # ── Framework detection ──
        for fw, checks in FRAMEWORK_SIGNATURES.items():
            pattern, check_type = checks
            matched = False
            if check_type == "content" and re.search(pattern, body, re.IGNORECASE):
                matched = True
            elif check_type == "content_or_header" and (
                re.search(pattern, body, re.IGNORECASE) or
                re.search(pattern, "\n".join(f"{k}: {v}" for k, v in headers.items()), re.IGNORECASE)
            ):
                matched = True

            if matched:
                fp.frameworks.append(fw)
                fp.all_matches.append(TechMatch(name=fw, category="framework", evidence=f"Pattern: {pattern}"))

        # ── CMS detection ──
        for cms, patterns in CMS_SIGNATURES.items():
            for pattern in patterns:
                if re.search(pattern, body, re.IGNORECASE):
                    fp.cms = cms
                    fp.all_matches.append(TechMatch(name=cms, category="cms", evidence=f"Pattern: {pattern}"))
                    break
            if fp.cms:
                break

        # ── JS library detection ──
        for lib, pattern in JS_LIB_SIGNATURES.items():
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                version = match.group(1) if match.lastindex else ""
                fp.js_libraries.append(f"{lib} {version}".strip())
                fp.all_matches.append(TechMatch(
                    name=lib, category="js_library", version=version,
                    evidence=f"Pattern: {pattern}"
                ))

        # ── Security headers check ──
        for header_name, header_key in SECURITY_HEADERS.items():
            fp.security_headers[header_name] = header_key.lower() in headers

        return fp
