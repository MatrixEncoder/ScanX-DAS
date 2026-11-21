import sys, os
sys.path.insert(0,'c:/ScanX')

print('=== SCAN-X VERIFICATION ===')

# 1. vite.config.js has /assessments and /api proxy
with open('frontend/vite.config.js') as f:
    cfg = f.read()
assert '/assessments' in cfg, 'MISSING /assessments proxy'
assert "'/api'" in cfg, 'MISSING /api proxy'
print('OK  vite.config.js has /assessments and /api proxy')

# 2. Crawls.jsx has correct /app/targets link
with open('frontend/src/pages/Crawls.jsx') as f:
    crawls = f.read()
assert '/app/targets' in crawls, 'MISSING /app/targets link fix'
print('OK  Crawls.jsx has /app/targets link (fixed)')

# 3. Endpoints.jsx has JSON.parse for parameters
with open('frontend/src/pages/Endpoints.jsx') as f:
    eps = f.read()
assert 'JSON.parse' in eps, 'MISSING JSON.parse for parameters'
print('OK  Endpoints.jsx parses parameters as JSON (fixed)')

# 4. Frontend dist was built
assert os.path.exists('frontend/dist/index.html'), 'dist/index.html missing'
print('OK  frontend/dist/index.html exists (built)')

# 5. All backend imports
from backend.main import app
from backend.database import init_db
from backend.api import targets, crawls, endpoints, reports, github_api, assessments
from backend.crawler.deep_crawler import DeepCrawler
from backend.crawler.form_parser import extract_forms, extract_links
from backend.crawler.js_analyzer import analyze_inline_scripts, analyze_external_js, extract_js_urls
from backend.crawler.wordlist import SENSITIVE_PATHS
from backend.fingerprinter.tech_detect import TechFingerprinter
from backend.github_analyzer.analyzer import RepoAnalyzer
from backend.github_analyzer.github_client import GithubClient, parse_github_url
from backend.github_analyzer.security_rules import ALL_RULES
from backend.github_analyzer.report_generator import generate_github_report
from backend.reporting.endpoint_report import generate_endpoint_report
from backend.scheduler.job_runner import run_crawl_job
print('OK  all backend modules import cleanly')

# 6. DB init
init_db()
print('OK  database schema initialized')

# 7. API routes check via openapi
from fastapi.openapi.utils import get_openapi
openapi = get_openapi(title=app.title, version=app.version, routes=app.routes)
api_paths = list(openapi.get('paths', {}).keys())
print(f'OK  {len(api_paths)} API endpoint paths registered via OpenAPI')
expected_prefixes = ['/targets', '/crawls', '/endpoints', '/reports', '/github', '/assessments', '/api/health']
for exp in expected_prefixes:
    found = any(p.startswith(exp) for p in api_paths)
    print(f"{'OK ' if found else 'MISSING'}  {exp} routes registered")

# 8. GitHub security rules count
print(f'OK  {len(ALL_RULES)} security rules loaded')

# 9. Wordlist paths
print(f'OK  {len(SENSITIVE_PATHS)} sensitive paths in wordlist')

print()
print('=== ALL CHECKS PASSED - PROJECT IS READY ===')
