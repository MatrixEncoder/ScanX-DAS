# Scan-X

> **Full-stack pentest reconnaissance platform**
> *B.Tech Final Year Cybersecurity Project*

Scan-X combines **endpoint discovery + tech fingerprinting** for web targets with **source code security analysis** for GitHub repositories, linked by a **correlation engine** that maps endpoints to source files and findings.

---

## Features

### Endpoint Discovery and Fingerprinting

- **Deep Crawling** — BFS with form parsing, JS endpoint extraction, wordlist-based discovery (90+ sensitive paths)
- **Technology Fingerprinting** — Detects frameworks, CMS, JS libraries, analytics tools, CDN providers
- **Categorized Reports** — HTML reports with endpoint inventory, Burp Suite test recommendations per endpoint
- **Background Job Runner** — Queued crawl sessions with real-time status tracking

### GitHub Repository Analyzer

- **40+ detection rules** — Hardcoded secrets, injection vulnerabilities, XSS, SSRF, misconfigurations
- **Smart file filtering** — Skips bundled/minified JS, binary files, node_modules, build artifacts
- **Private repo support** — PAT authentication for cloning private repos
- **Vulnerability reports** — Categorized HTML reports grouped by file, severity, and category

### Assessment System

- **Web Recon** — Target URL only; runs deep crawler + fingerprinting
- **Repository Scan** — GitHub repo URL only; runs security analysis
- **Full Assessment** — Both URL + repo; runs crawler + analyzer + correlation engine

### Correlation Engine

- **Route Matching** — Maps endpoints to source file routes using framework patterns (Express, Flask, Django, Next.js)
- **Source Mapping** — Links endpoints to repository files via URL patterns and route definitions
- **Confidence Scoring** — Weighted scoring normalized to 0-100 with matched evidence

### Attack Surface View

- **Tree visualization** — Endpoints grouped by source with linked source files and findings
- **Quick navigation** — Jump from endpoint to correlated repository findings

### Dark Glassmorphism UI

- **Dark theme** — Near-black base with glass cards and vibrant accent colors
- **Landing page** — Hero section with feature cards
- **Dashboard** — KPI cards, pie charts, bar charts
- **Assessment wizard** — Mode selection, configuration, progress animation, results with correlations

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Git

### Setup

```bash
git clone https://github.com/your-username/Scan-X.git
cd Scan-X
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

### Run

```bash
python run.py
```

Open **http://127.0.0.1:8000** in your browser.

---

## Project Structure

```
Scan-X/
├── run.py                          # Entry point
├── backend/
│   ├── main.py                     # FastAPI app + static serving
│   ├── database.py                 # SQLAlchemy engine + session
│   ├── models.py                   # ORM models
│   ├── schemas.py                  # Pydantic v2 schemas
│   ├── api/
│   │   ├── targets.py              # Target CRUD
│   │   ├── crawls.py               # Crawl management
│   │   ├── endpoints.py            # Endpoint listing + stats
│   │   ├── reports.py              # Report generation
│   │   ├── github_api.py           # GitHub scan API
│   │   └── assessments.py          # Assessment CRUD + correlation
│   ├── crawler/                    # BFS crawler + form/JS/wordlist
│   ├── fingerprinter/              # Technology detection
│   ├── github_analyzer/            # Security rules + analysis
│   ├── correlation/                # Route matching + scoring
│   ├── reporting/                  # HTML report templates
│   └── scheduler/                  # Background job runner
├── frontend/
│   └── src/
│       ├── App.jsx                 # Routes
│       ├── index.css               # Dark glassmorphism theme
│       ├── pages/                  # Dashboard, Assess, etc.
│       ├── components/             # Sidebar
│       └── api/client.js           # Axios API client
└── database/
    └── scanx.db                    # SQLite (auto-created)
```

---

## Detection Rules

| Category | Rule IDs | What it catches |
|----------|----------|-----------------|
| Secrets | SEC-001 to SEC-024 | AWS keys, GitHub tokens, Stripe keys, JWT secrets, database passwords |
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
| GET | `/targets/` | List targets |
| POST | `/targets/` | Create target |
| POST | `/crawls/` | Start crawl |
| GET | `/endpoints/` | List endpoints |
| GET | `/endpoints/dashboard` | Dashboard stats |
| POST | `/github/analyze` | Start GitHub scan |
| GET | `/github/analyses` | List analyses |
| GET | `/github/analyses/{id}` | Get analysis |
| GET | `/github/analyses/{id}/findings` | Get findings |
| POST | `/github/analyses/{id}/report` | Generate report |
| POST | `/assessments/web` | Web assessment |
| POST | `/assessments/repository` | Repo assessment |
| POST | `/assessments/full` | Full assessment |
| GET | `/assessments/` | List assessments |
| GET | `/assessments/{id}` | Get assessment |
| GET | `/assessments/{id}/correlations` | Get correlations |
| POST | `/assessments/{id}/report` | Generate report |
| GET | `/assessments/{id}/report/download` | Download report |
| GET | `/api/docs` | Swagger docs |

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
