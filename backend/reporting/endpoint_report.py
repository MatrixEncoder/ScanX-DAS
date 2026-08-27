"""
endpoint_report.py — HTML report generator for endpoint discovery results.

Groups endpoints by path category, generates Burp Suite test recommendations,
and renders a detailed pentest-ready report.
"""

import os
import re
import json
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


# ── Path Categorization ─────────────────────────────────────────────────────

CATEGORY_RULES = [
    ("Authentication", re.compile(r"/(auth|login|signin|signup|register|oauth|saml|sso|token|session|password|forgot|reset|confirm)", re.I)),
    ("Admin", re.compile(r"/(admin|dashboard|panel|manage|console|cms|backoffice)", re.I)),
    ("API", re.compile(r"/(api|graphql|rest|json|xml|rpc|gateway)", re.I)),
    ("Users", re.compile(r"/(user|account|profile|me|member|people|person)", re.I)),
    ("Search", re.compile(r"/(search|query|find|lookup|filter|autocomplete|suggest)", re.I)),
    ("Upload", re.compile(r"/(upload|file|import|export|download|attach|media|image|avatar|document)", re.I)),
    ("Payment", re.compile(r"/(pay|checkout|billing|invoice|subscription|plan|price|cart|order)", re.I)),
    ("Notification", re.compile(r"/(notif|alert|message|email|mail|sms|push|webhook)", re.I)),
    ("Settings", re.compile(r"/(setting|config|preference|option|toggle|feature)", re.I)),
    ("Comments", re.compile(r"/(comment|review|feedback|rating|vote)", re.I)),
    ("Blog/Posts", re.compile(r"/(blog|post|article|news|feed|rss|entry)", re.I)),
    ("Static Assets", re.compile(r"/(static|assets|css|js|font|img|image|icon|favicon|robots\.txt|sitemap)", re.I)),
    ("Docs", re.compile(r"/(doc|swagger|openapi|spec|redoc|help|faq|wiki)", re.I)),
    ("Health", re.compile(r"/(health|status|ready|live|ping|version|info|metrics)", re.I)),
]

DEFAULT_CATEGORY = "Other"


def categorize_endpoint(url: str) -> str:
    """Assign a category to an endpoint based on its URL path."""
    try:
        path = urlparse(url).path.lower()
    except Exception:
        path = url.lower()
    for cat_name, pattern in CATEGORY_RULES:
        if pattern.search(path):
            return cat_name
    return DEFAULT_CATEGORY


# ── Burp Suite Test Recommendations ─────────────────────────────────────────

def generate_burp_tests(ep) -> list:
    """
    Generate a list of recommended Burp Suite tests for an endpoint.
    Returns list of dicts: {test_name, tool, description, priority}
    """
    tests = []
    methods = [m.strip().upper() for m in (ep.methods or "GET").split(",")]
    params = []
    if ep.parameters:
        try:
            params = json.loads(ep.parameters) if isinstance(ep.parameters, str) else ep.parameters
        except Exception:
            params = []
    has_params = len(params) > 0
    is_api = ep.is_api
    has_login = ep.has_login_form
    is_post = "POST" in methods
    is_put = "PUT" in methods or "PATCH" in methods
    is_delete = "DELETE" in methods
    is_redirect = bool(ep.redirect_url)
    status = ep.status_code

    # ── Always recommended ──
    tests.append({
        "test_name": "Send to Repeater",
        "tool": "Repeater",
        "description": "Manual request tampering — modify parameters, headers, cookies to test for injection, IDOR, and logic flaws.",
        "priority": "High",
    })

    if has_params:
        tests.append({
            "test_name": "SQL Injection (SQLi)",
            "tool": "Scanner / Intruder",
            "description": f"Test {len(params)} parameter(s) for SQL injection. Inject: ', \"OR 1=1, UNION SELECT, blind/SRL payloads.",
            "priority": "Critical",
        })
        tests.append({
            "test_name": "Cross-Site Scripting (XSS)",
            "tool": "Scanner / Intruder",
            "description": "Inject <script>alert(1)</script>, event handlers, and encoded payloads in each parameter.",
            "priority": "Critical",
        })
        tests.append({
            "test_name": "Parameter Tampering",
            "tool": "Intruder",
            "description": f"Fuzz parameters: {', '.join(p.get('name', '?') for p in params[:6])}. Try type juggling, boundary values, negative numbers.",
            "priority": "High",
        })

    if is_post or is_put:
        tests.append({
            "test_name": "Mass Assignment",
            "tool": "Repeater",
            "description": "Add unexpected fields (admin, role, user_id, price, is_verified) to request body to test for privilege escalation.",
            "priority": "High",
        })
        tests.append({
            "test_name": "Content-Type Switching",
            "tool": "Repeater",
            "description": "Change Content-Type between JSON, form-data, XML, and x-www-form-urlencoded. Test for XXE and parser differential.",
            "priority": "Medium",
        })

    if is_api:
        tests.append({
            "test_name": "API Authorization Bypass",
            "tool": "Repeater",
            "description": "Remove/replace auth headers, test with different user tokens, try IDOR on path and body parameters.",
            "priority": "Critical",
        })
        tests.append({
            "test_name": "Rate Limiting",
            "tool": "Intruder",
            "description": "Send 100+ rapid requests to test for rate limiting. Look for OTP bypass, brute-force opportunities.",
            "priority": "Medium",
        })

    if has_login:
        tests.append({
            "test_name": "Brute Force / Credential Stuffing",
            "tool": "Intruder",
            "description": "Test with common credentials, check for account lockout, password policy enforcement, and 2FA bypass.",
            "priority": "Critical",
        })
        tests.append({
            "test_name": "Session Management",
            "tool": "Repeater",
            "description": "Test session fixation, token entropy, cookie flags (HttpOnly, Secure, SameSite), and session invalidation.",
            "priority": "High",
        })

    if is_redirect:
        tests.append({
            "test_name": "Open Redirect",
            "tool": "Repeater",
            "description": "Inject external URLs in redirect parameters. Test: //evil.com, /\/evil.com, url=//evil.com.",
            "priority": "High",
        })

    if is_delete:
        tests.append({
            "test_name": "IDOR on Delete",
            "tool": "Repeater",
            "description": "Try deleting resources belonging to other users by changing ID in path/body.",
            "priority": "Critical",
        })

    # ── Status-based tests ──
    if status in (301, 302, 307, 308):
        tests.append({
            "test_name": "Redirect Validation",
            "tool": "Repeater",
            "description": "Verify the redirect target. Test for open redirect by manipulating the Location header value.",
            "priority": "High",
        })

    if status == 200 and is_api:
        tests.append({
            "test_name": "Verb Tampering",
            "tool": "Repeater",
            "description": "Send GET/POST/PUT/PATCH/DELETE/OPTIONS/HEAD to the same endpoint. Test for hidden functionality.",
            "priority": "Medium",
        })

    # ── Path-based tests ──
    url_lower = (ep.url or "").lower()
    if any(x in url_lower for x in ["upload", "file", "import", "avatar", "document"]):
        tests.append({
            "test_name": "File Upload Bypass",
            "tool": "Repeater",
            "description": "Upload files with double extensions, polyglot files, magic byte manipulation, and path traversal in filename.",
            "priority": "Critical",
        })

    if any(x in url_lower for x in ["search", "query", "find", "q=", "s="]):
        tests.append({
            "test_name": "NoSQL Injection",
            "tool": "Repeater",
            "description": "Inject MongoDB operators: {$ne: null}, {$gt: ''}, {$regex: '.*'}. Test for search bypass.",
            "priority": "High",
        })

    if any(x in url_lower for x in ["password", "reset", "forgot", "otp", "verify"]):
        tests.append({
            "test_name": "OTP/Reset Bypass",
            "tool": "Repeater",
            "description": "Test for race conditions, predictable tokens, client-side validation, and response manipulation.",
            "priority": "Critical",
        })

    if "graphql" in url_lower:
        tests.append({
            "test_name": "GraphQL Introspection",
            "tool": "Repeater",
            "description": "Send {__schema{types{name,fields{name}}}} to dump the schema. Test for injection in query arguments.",
            "priority": "High",
        })

    # ── Universal extra test ──
    tests.append({
        "test_name": "CORS Misconfiguration",
        "tool": "Repeater",
        "description": "Set Origin header to: null, evil.com, target.com.evil.com. Check if Access-Control-Allow-Origin reflects it.",
        "priority": "Medium",
    })

    return tests


# ── Report Generation ───────────────────────────────────────────────────────

def generate_endpoint_report(crawl, target, endpoints, tech_data, output_path):
    """Render and save an HTML endpoint discovery report."""
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    template = env.get_template("endpoint_report.html")

    # Group by source
    by_source = {}
    for ep in endpoints:
        by_source.setdefault(ep.source, []).append(ep)

    # Group by category
    by_category = {}
    for ep in endpoints:
        cat = categorize_endpoint(ep.url)
        by_category.setdefault(cat, []).append(ep)

    # Generate Burp tests per endpoint
    burp_map = {}
    for ep in endpoints:
        burp_map[ep.id] = generate_burp_tests(ep)

    # Collect all unique Burp test names for summary
    all_burp_tests = set()
    for tests in burp_map.values():
        for t in tests:
            all_burp_tests.add(t["test_name"])

    # Tech summary
    tech = tech_data if isinstance(tech_data, dict) else {}

    context = {
        "crawl": crawl,
        "target": target,
        "endpoints": endpoints,
        "by_source": by_source,
        "by_category": by_category,
        "burp_map": burp_map,
        "all_burp_tests": sorted(all_burp_tests),
        "tech": tech,
        "total": len(endpoints),
        "generated_at": (datetime.now(timezone(timedelta(hours=5, minutes=30)))).strftime("%Y-%m-%d %H:%M:%S IST"),
    }

    html = template.render(**context)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Copy logo to reports directory for local HTML viewing
    logo_src = os.path.join(TEMPLATES_DIR, "scanx-logo.png")
    logo_dst = os.path.join(os.path.dirname(output_path), "scanx-logo.png")
    if os.path.exists(logo_src) and not os.path.exists(logo_dst):
        import shutil
        shutil.copy2(logo_src, logo_dst)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
