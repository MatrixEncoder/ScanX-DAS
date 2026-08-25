# Scan-X — Endpoint Discovery & Repository Security Analyzer

> **Full-stack pentest reconnaissance platform**
> *B.Tech Final Year Cybersecurity Project*

Scan-X combines **endpoint discovery + tech fingerprinting** for web targets with **source code security analysis** for GitHub repositories, linked by a **correlation engine** that maps endpoints to source files and findings. Built for pentesters who need quick attack surface mapping and vulnerability detection in one place.

---

## Features

### Endpoint Discovery & Fingerprinting
- **Deep Crawling** — BFS with form parsing, JS endpoint extraction, wordlist-based discovery (90+ sensitive paths)
- **Technology Fingerprinting** — Detects frameworks, CMS, JS libraries, analytics tools, CDN providers
- **Categorized Reports** — HTML reports with endpoint inventory, Burp Suite test recommendations per endpoint
- **Background Job Runner** — Queued crawl sessions with real-time status tracking

### GitHub Repository Analyzer
- **40+ detection rules** — Hardcoded secrets (API keys, tokens, passwords), injection vulnerabilities, XSS, SSRF, misconfigurations
- **Smart file filtering** — Skips bundled/minified JS, binary files, node_modules, build artifacts
- **Private repo support** — PAT authentication for cloning private repos
- **Vulnerability reports** — Categorized HTML reports grouped by file, severity, and category

### Assessment System (3 Modes)
- **Web Recon** — Target URL only; runs deep crawler + fingerprinting
- **Repository Scan** — GitHub repo URL only; runs security analysis
- **Full Assessment** — Both URL + repo; runs crawler + analyzer + correlation engine

### Correlation Engine
- **Route Matching** — Maps discovered endpoints to source file routes using framework patterns (Express, Flask, Django, Next.js)
- **Source Mapping** — Links endpoints to repository files via URL patterns, route definitions, and controller references
- **Confidence Scoring** — Weighted scoring (exact route: 40%, method match: 20%, reference match: 20%, param match: 10%, framework: 10%) normalized to 0–100
- **Evidence-Based** — Each correlation includes matched evidence for transparency

### Attack Surface View
- **Tree visualization** — Endpoints grouped by source (link/form/js/wordlist) with linked source files and findings
- **Quick navigation** — Jump from endpoint to its correlated repository findings

### Dark Glassmorphism UI
- **Dark theme** — Near-black base (`#09090b`) with glass cards and vibrant accent colors
- **Landing page** — Hero section with feature cards
- **Dashboard** — KPI cards, pie charts (endpoint sources, crawl status), bar charts (endpoints by method)
- **Assessment wizard** — Mode selection → configuration → progress animation → results with correlations

---

## Quick Start

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **Git**

### Setup

```bash
# Clone the repo
git clone https://github.com/your-username/Scan-X.git
cd Scan-X

# Install backend dependencies
pip install -r backend/requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### Run

```bash
python run.py
```

Open **http://127.0.0.1:8000** in your browser.

That's it — one command serves both the API and the built React frontend.

---

## Project Structure

```
Scan-X/
├── run.py                          # Entry point — starts API + frontend server
├── backend/
│   ├── main.py                     # FastAPI app, static file serving, SPA catch-all
│   ├── database.py                 # SQLAlchemy engine + session
│   ├── models.py                   # ORM: Target, Crawl, Endpoint, Report, GithubAnalysis,
│   │                               #   Assessment, Correlation, CorrelationEvidence
│   ├── schemas.py                  # Pydantic v2 request/response schemas
│   ├── api/
│   │   ├── targets.py              # Target CRUD (auto-adds URL scheme)
│   │   ├── crawls.py               # Crawl session management
│   │   ├── endpoints.py            # Endpoint listing, stats, dashboard
│   │   ├── reports.py              # Report generation + download
│   │   ├── github_api.py           # GitHub scan REST API + background jobs
│   │   └── assessments.py          # Assessment CRUD, correlation, full reports
│   ├── crawler/
│   │   ├── deep_crawler.py         # BFS crawler with form + JS + wordlist support
│   │   ├── form_parser.py          # HTML form extraction
│   │   ├── js_analyzer.py          # JS endpoint URL extraction
│   │   └── wordlist.py             # 90+ sensitive path wordlist
│   ├── fingerprinter/
│   │   └── tech_detect.py          # Technology fingerprinting engine
│   ├── github_analyzer/
│   │   ├── github_client.py        # GitHub API + git clone with PAT auth
│   │   ├── security_rules.py       # 40+ vulnerability detection rules
│   │   ├── analyzer.py             # RepoAnalyzer orchestrator
│   │   ├── report_generator.py     # HTML report generator (IST timestamps)
│   │   └── templates/              # Report HTML templates
│   ├── correlation/
│   │   ├── engine.py               # CorrelationEngine orchestrator
│   │   ├── route_matcher.py        # Framework-aware route matching
│   │   ├── source_mapper.py        # Repo index + reference finding
│   │   └── scoring.py              # Weighted scoring (0–100)
│   ├── reporting/
│   │   ├── endpoint_report.py      # Categorized endpoint report with Burp tests
│   │   └── templates/              # Report HTML templates
│   └── scheduler/
│       └── job_runner.py           # Background crawl job runner
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Routes: / → Landing, /app/* → AppLayout
│   │   ├── index.css               # Dark glassmorphism design system
│   │   ├── pages/
│   │   │   ├── Landing.jsx         # Hero + feature cards
│   │   │   ├── Dashboard.jsx       # KPIs + charts + recent crawls
│   │   │   ├── Assess.jsx          # Assessment wizard (3 modes)
│   │   │   ├── AttackSurface.jsx   # Correlated endpoint tree view
│   │   │   ├── GithubScan.jsx      # GitHub repository scanner
│   │   │   └── Reports.jsx         # Report listing + download
│   │   ├── components/
│   │   │   └── Sidebar.jsx         # Glass sidebar with logo
│   │   └── api/client.js           # Axios API client
│   └── vite.config.js              # Dev proxy config
└── database/
    └── scanx.db                    # SQLite database (auto-created)
```

---

## GitHub Analyzer — Detection Rules

| Category | Rule IDs | What it catches |
|----------|----------|-----------------|
| Secrets | SEC-001 to SEC-024 | AWS keys, GitHub tokens, Stripe keys, JWT secrets, database passwords, API keys |
| Injection | VUL-001 to VUL-005 | SQL injection, command injection, template injection |
| XSS | VUL-006 | innerHTML, document.write, eval usage |
| SSRF | VUL-007 to VUL-008 | Server-side request forgery patterns |
| Redirect | VUL-009 to VUL-011 | Open redirect vulnerabilities |
| Config | VUL-012 to VUL-020 | Debug mode, CORS misconfiguration, insecure cookies |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/targets/` | List all targets |
| POST | `/targets/` | Create a new target |
| POST | `/crawls/` | Start a crawl session |
| GET | `/endpoints/` | List discovered endpoints |
| GET | `/endpoints/dashboard` | Dashboard stats |
| POST | `/github/analyze` | Start GitHub repo scan |
| GET | `/github/analyses` | List all GitHub analyses |
| GET | `/github/analyses/{id}` | Get analysis status |
| GET | `/github/analyses/{id}/findings` | Get scan findings |
| POST | `/github/analyses/{id}/report` | Generate HTML report |
| POST | `/assessments/web` | Web-only assessment |
| POST | `/assessments/repository` | Repo-only assessment |
| POST | `/assessments/full` | Full assessment (web + repo + correlation) |
| GET | `/assessments/` | List all assessments |
| GET | `/assessments/{id}` | Get assessment details |
| GET | `/assessments/{id}/correlations` | Get correlation results |
| POST | `/assessments/{id}/report` | Generate full assessment report |
| GET | `/assessments/{id}/report/download` | Download assessment report |
| GET | `/api/docs` | Interactive API docs (Swagger) |

---

## Tech Stack

- **Backend:** Python 3.13, FastAPI, SQLAlchemy, SQLite
- **Frontend:** React 18, Vite 6, React Router 6, Recharts, Lucide Icons
- **GitHub Integration:** GitHub REST API + git clone fallback
- **Scanning:** Pattern-based rule engine (regex), BFS crawling
- **Correlation:** Weighted scoring engine with framework-aware route matching
- **UI:** Dark glassmorphism design with glass cards and vibrant accents

---

*Scan-X — B.Tech Final Year Cybersecurity Project*
#   S c a n X - D A S  
 