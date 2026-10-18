"""
deep_crawler.py — Deep web crawler for endpoint discovery.

Multi-strategy crawler that:
1. BFS spider following HTML links
2. Form extraction and submission
3. JavaScript endpoint extraction (inline + external)
4. Hidden path discovery via wordlist
5. API endpoint detection

All requests use the same session for cookie persistence.
"""

import heapq
import logging
import re
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

import requests
from bs4 import BeautifulSoup

from backend.crawler.form_parser import (
    extract_forms, extract_links, FormInfo
)
from backend.crawler.js_analyzer import (
    analyze_inline_scripts, analyze_external_js, extract_js_urls
)
from backend.crawler.wordlist import SENSITIVE_PATHS

logger = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)

# ── URL Priority Scoring ───────────────────────────────────────────────────
# High-value paths an attacker would actually target. Higher score = crawled first.

HIGH_VALUE_PATTERNS = [
    # Auth / login — highest priority
    (r"/(login|signin|sign-in|log-in|auth|oauth|sso|saml|token|session)", 10),
    (r"/(register|signup|sign-up|create-account|join)", 9),
    (r"/(password|forgot|reset|otp|verify|confirm-email|mfa|2fa|totp)", 9),
    # Admin / dashboard
    (r"/(admin|dashboard|panel|manage|console|backoffice|wp-admin|cpanel)", 10),
    # API endpoints
    (r"/(api|graphql|rest|rpc|webhook|json)", 8),
    # User / account
    (r"/(user|account|profile|me|member|settings|preferences)", 7),
    # Upload / file
    (r"/(upload|file|import|export|download|attach|media|avatar|document)", 7),
    # Payment
    (r"/(pay|checkout|billing|invoice|subscription|cart|order|payment)", 7),
    # Search / query
    (r"/(search|query|find|lookup|filter)", 6),
    # Config / env / debug
    (r"/(config|env|debug|test|staging|setup|install|phpinfo|info)", 8),
    # Database / backup
    (r"/(backup|dump|db|database|sql|phpmyadmin|adminer)", 8),
    # Comments / feedback
    (r"/(comment|review|feedback|rating)", 5),
    # Notification
    (r"/(notif|alert|message|mail|sms|push)", 5),
]

# Low-value / junk URLs to skip entirely
SKIP_URL_PATTERNS = [
    # Static assets
    r"\.(png|jpg|jpeg|gif|svg|ico|webp|avif|bmp|tiff?)\b",
    r"\.(css|woff2?|ttf|eot|otf)\b",
    r"\.(mp4|webm|ogg|mp3|wav|flac|avi|mov|wmv)\b",
    r"\.(zip|tar|gz|rar|7z|iso|dmg|exe|msi|apk|deb|rpm)\b",
    r"\.(pdf|docx?|xlsx?|pptx?|csv|txt|md|log)\b",
    # Social / external share links
    r"(facebook\.com|twitter\.com|x\.com|linkedin\.com|instagram\.com|youtube\.com|t\.co|bit\.ly)",
    # Common junk paths
    r"/(wp-json/wp/v2/(users|comments)|xmlrpc\.php|wp-cron\.php)",
    r"/(apple-touch-icon|favicon|browserconfig|manifest|crossdomain|robots|sitemap)",
    # Calendar / archive pagination
    r"/(archive|tag|category|author|page|feed|rss|atom)/?\d",
    # Analytics / tracking pixels
    r"(google-analytics|googletagmanager|facebook\.net|hotjar|mixpanel|segment\.com|doubleclick)",
    # Font/CDN paths
    r"/(fonts\.googleapis|cdn\.|unpkg\.com|jsdelivr|cdnjs|bootstrapcdn|cloudflare)",
]

SKIP_URL_RE = [re.compile(p, re.I) for p in SKIP_URL_PATTERNS]

# Query params that indicate pagination/sorting — skip these URL variants
JUNK_QUERY_PARAMS = {"page", "p", "offset", "sort", "order", "dir", "filter",
                     "ref", "source", "utm_source", "utm_medium", "utm_campaign",
                     "utm_term", "utm_content", "fbclid", "gclid", "mc_cid", "mc_eid",
                     "lang", "locale", "theme", "mode", "view", "tab", "print"}


def _score_url(url: str) -> int:
    """Return a priority score for a URL. Higher = more important to crawl first."""
    path = urlparse(url).path.lower()
    score = 3  # baseline for any same-domain URL
    for pattern, points in HIGH_VALUE_PATTERNS:
        if re.search(pattern, path):
            score = max(score, points)
    # Bonus for query parameters (often indicate input points)
    if urlparse(url).query:
        score += 1
    return score


def _should_skip_url(url: str, base_domain: str) -> bool:
    """Return True if this URL is low-value and not worth crawling."""
    parsed = urlparse(url)
    # External domain
    if parsed.netloc and parsed.netloc != base_domain:
        return True
    # Skip junk query params (pagination, sorting, tracking)
    if parsed.query:
        params = parse_qs(parsed.query)
        # If ALL query params are junk, skip the URL
        if params and all(k.lower() in JUNK_QUERY_PARAMS for k in params):
            return True
    # Skip junk patterns
    for pattern in SKIP_URL_RE:
        if pattern.search(url):
            return True
    return False


@dataclass
class EndpointInfo:
    """Complete information about a discovered endpoint."""
    url: str
    methods: List[str] = field(default_factory=lambda: ["GET"])
    status_code: int = 0
    content_type: str = ""
    content_length: int = 0
    title: str = ""
    redirect_url: str = ""
    parameters: List[Dict[str, str]] = field(default_factory=list)
    form_count: int = 0
    source: str = ""  # How it was discovered: link, form, js, wordlist
    depth: int = 0
    response_headers: Dict[str, str] = field(default_factory=dict)
    has_login_form: bool = False
    is_api: bool = False


@dataclass
class CrawlResult:
    """Complete crawl results."""
    target_url: str
    endpoints: List[EndpointInfo] = field(default_factory=list)
    total_requests: int = 0
    crawl_duration: float = 0.0
    pages_crawled: int = 0
    forms_found: int = 0
    js_files_analyzed: int = 0
    hidden_paths_found: int = 0
    errors: List[str] = field(default_factory=list)


class DeepCrawler:
    """
    Deep web crawler that discovers all endpoints on a target.

    Strategies:
    - BFS link following
    - Form extraction and parameter discovery
    - JavaScript analysis (inline + external)
    - Hidden path wordlist probing
    - API endpoint detection
    """

    def __init__(
        self,
        target_url: str,
        max_depth: int = 2,
        max_pages: int = 80,
        max_requests: int = 200,
        timeout: int = 10,
        crawl_forms: bool = True,
        crawl_js: bool = True,
        probe_hidden: bool = True,
    ):
        url = target_url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        self.target_url = url.rstrip("/")
        self.base_domain = urlparse(self.target_url).netloc
        self.base_scheme = urlparse(self.target_url).scheme
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.max_requests = max_requests
        self.timeout = timeout
        self.crawl_forms = crawl_forms
        self.crawl_js = crawl_js
        self.probe_hidden = probe_hidden

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ScanX-DeepCrawler/1.0"})
        self.session.verify = False

        # Tracking
        self.visited: set = set()
        self.endpoint_map: Dict[str, EndpointInfo] = {}
        self.request_count = 0
        self.start_time = 0.0
        self.errors: List[str] = []

    def crawl(self) -> CrawlResult:
        """Execute the full deep crawl and return results."""
        self.start_time = time.time()
        logger.info(f"[Crawler] Starting deep crawl of {self.target_url}")

        # Phase 1: BFS link crawl
        self._bfs_crawl()

        # Phase 2: Hidden path probing
        if self.probe_hidden:
            self._probe_hidden_paths()

        # Phase 3: Extract JS endpoints from already-crawled pages
        if self.crawl_js:
            self._analyze_collected_js()

        duration = time.time() - self.start_time
        endpoints = sorted(self.endpoint_map.values(), key=lambda e: e.url)

        result = CrawlResult(
            target_url=self.target_url,
            endpoints=endpoints,
            total_requests=self.request_count,
            crawl_duration=round(duration, 2),
            pages_crawled=len([e for e in endpoints if e.content_type and "text/html" in e.content_type]),
            forms_found=sum(e.form_count for e in endpoints),
            js_files_analyzed=self.request_count,
            hidden_paths_found=len([e for e in endpoints if e.source == "wordlist"]),
            errors=self.errors,
        )

        logger.info(
            f"[Crawler] Complete: {len(endpoints)} endpoints found in "
            f"{duration:.1f}s ({self.request_count} requests)"
        )
        return result

    # ── Phase 1: Priority BFS Crawl ──────────────────────────────────────

    def _bfs_crawl(self):
        """Priority-queue crawl: high-value endpoints first, skip junk URLs."""
        # heap entries: (-priority, counter, url, depth) — heapq is a min-heap
        counter = 0
        initial_score = _score_url(self.target_url)
        queue: list = [(-initial_score, counter, self.target_url, 0)]
        js_files_to_analyze: List[str] = []
        enqueued: set = {self.target_url}

        while queue and len(self.visited) < self.max_pages and self.request_count < self.max_requests:
            _, _, url, depth = heapq.heappop(queue)

            if url in self.visited or depth > self.max_depth:
                continue

            self.visited.add(url)
            resp = self._fetch(url)

            if resp is None:
                continue

            # Record this endpoint
            self._record_endpoint(url, resp, depth=depth, source="link")

            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type:
                continue

            html = resp.text

            # Extract page title
            self._set_title(url, html)

            # Extract links
            links = extract_links(html, url)
            for link in links:
                if link in self.visited or link in enqueued:
                    continue
                if _should_skip_url(link, self.base_domain):
                    continue
                if depth + 1 > self.max_depth:
                    continue
                counter += 1
                score = _score_url(link)
                heapq.heappush(queue, (-score, counter, link, depth + 1))
                enqueued.add(link)

            # Extract forms
            if self.crawl_forms:
                forms = extract_forms(html, url)
                for form in forms:
                    self._process_form(form, depth)
                    action = form.action
                    if (action and action not in self.visited and action not in enqueued
                            and not _should_skip_url(action, self.base_domain)
                            and depth + 1 <= self.max_depth):
                        counter += 1
                        score = _score_url(action) + 2  # forms get a small boost
                        heapq.heappush(queue, (-score, counter, action, depth + 1))
                        enqueued.add(action)

            # Collect JS file URLs for phase 3
            if self.crawl_js:
                js_urls = extract_js_urls(html, url)
                js_files_to_analyze.extend(js_urls)

                # Extract inline JS endpoints
                inline_endpoints = analyze_inline_scripts(html, url)
                for ep in inline_endpoints:
                    if ep in self.visited or ep in enqueued:
                        continue
                    if _should_skip_url(ep, self.base_domain):
                        continue
                    counter += 1
                    score = _score_url(ep)
                    heapq.heappush(queue, (-score, counter, ep, depth + 1))
                    enqueued.add(ep)

    # ── Phase 2: Hidden Path Probing ───────────────────────────────────

    def _probe_hidden_paths(self):
        """Probe common hidden/sensitive paths on the target."""
        logger.info(f"[Crawler] Probing {len(SENSITIVE_PATHS)} hidden paths...")

        for path in SENSITIVE_PATHS:
            if self.request_count >= self.max_requests:
                break

            url = self.target_url + path
            if url in self.visited:
                continue

            resp = self._fetch(url)
            if resp is None:
                continue

            status = resp.status_code
            # Record if accessible (200, 301, 302, 403 — all indicate path exists)
            if status in (200, 301, 302, 403, 405):
                self._record_endpoint(
                    url, resp, depth=0, source="wordlist",
                    status_override=status
                )

    # ── Phase 3: JS Analysis ───────────────────────────────────────────

    def _analyze_collected_js(self):
        """Analyze external JS files collected during BFS crawl."""
        js_urls = list(set(
            e.url for e in self.endpoint_map.values()
            if e.url.endswith(".js") or "javascript" in e.content_type
        ))

        if not js_urls:
            return

        logger.info(f"[Crawler] Analyzing {len(js_urls)} JavaScript files...")
        js_endpoints = analyze_external_js(js_urls[:20], self.target_url)

        for ep_url in js_endpoints:
            if ep_url not in self.visited and ep_url not in self.endpoint_map:
                resp = self._fetch(ep_url)
                if resp:
                    self._record_endpoint(ep_url, resp, depth=0, source="js")

    # ── Helpers ─────────────────────────────────────────────────────────

    def _fetch(self, url: str) -> Optional[requests.Response]:
        """Fetch a URL with error handling."""
        if self.request_count >= self.max_requests:
            return None

        self.request_count += 1
        try:
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            return resp
        except requests.exceptions.SSLError:
            # Retry without verification
            try:
                resp = self.session.get(url, timeout=self.timeout, allow_redirects=True, verify=False)
                return resp
            except Exception as e:
                self.errors.append(f"SSL Error: {url} — {e}")
                return None
        except requests.exceptions.ConnectionError as e:
            self.errors.append(f"Connection Error: {url} — {e}")
            return None
        except requests.exceptions.Timeout:
            self.errors.append(f"Timeout: {url}")
            return None
        except Exception as e:
            self.errors.append(f"Error: {url} — {e}")
            return None

    def _record_endpoint(
        self,
        url: str,
        resp: requests.Response,
        depth: int = 0,
        source: str = "link",
        status_override: int = 0,
    ):
        """Record or update an endpoint in the endpoint map."""
        # Normalize URL (strip fragments, trailing slashes for grouping)
        normalized = url.split("#")[0].rstrip("/") or url.split("#")[0]

        status = status_override or resp.status_code
        content_type = resp.headers.get("content-type", "")
        content_length = len(resp.content)
        redirect_url = resp.url if resp.url != url else ""

        # Check if this is an API endpoint
        is_api = any(p in normalized.lower() for p in [
            "/api/", "/v1/", "/v2/", "/graphql", "/rest/", "/json"
        ])

        # Check for login forms
        has_login = False
        if "text/html" in content_type:
            body_lower = resp.text.lower()
            has_login = any(kw in body_lower for kw in [
                "login", "signin", "sign-in", "log-in", "password",
            ])

        # Extract title
        title = ""
        if "text/html" in content_type:
            try:
                soup = BeautifulSoup(resp.text[:5000], "html.parser")
                if soup.title and soup.title.string:
                    title = soup.title.string.strip()[:100]
            except Exception:
                pass

        # Extract parameters from URL
        parsed = urlparse(url)
        params = []
        if parsed.query:
            for name in parse_qs(parsed.query):
                params.append({"name": name, "type": "query", "source": "url"})

        if normalized in self.endpoint_map:
            existing = self.endpoint_map[normalized]
            # Add method if new
            method = resp.request.method if hasattr(resp, 'request') else "GET"
            if method not in existing.methods:
                existing.methods.append(method)
        else:
            self.endpoint_map[normalized] = EndpointInfo(
                url=normalized,
                methods=["GET"],
                status_code=status,
                content_type=content_type,
                content_length=content_length,
                title=title,
                redirect_url=redirect_url,
                parameters=params,
                source=source,
                depth=depth,
                response_headers=dict(resp.headers),
                has_login_form=has_login,
                is_api=is_api,
            )

    def _process_form(self, form: FormInfo, depth: int):
        """Process a discovered form and record its endpoint."""
        if form.action in self.endpoint_map:
            existing = self.endpoint_map[form.action]
            existing.form_count += 1
            if not existing.parameters and form.parameter_names:
                existing.parameters = [
                    {"name": n, "type": "form", "source": "form"}
                    for n in form.parameter_names
                ]
        else:
            self.endpoint_map[form.action] = EndpointInfo(
                url=form.action,
                methods=[form.method],
                content_type="text/html",
                parameters=[
                    {"name": n, "type": "form", "source": "form"}
                    for n in form.parameter_names
                ],
                form_count=1,
                source="form",
                depth=depth,
            )

    def _set_title(self, url: str, html: str):
        """Extract and set the page title for an endpoint."""
        if url in self.endpoint_map:
            try:
                soup = BeautifulSoup(html[:5000], "html.parser")
                if soup.title and soup.title.string:
                    self.endpoint_map[url].title = soup.title.string.strip()[:100]
            except Exception:
                pass
