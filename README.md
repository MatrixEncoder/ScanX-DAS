# Scan-X

> **Full-stack pentest reconnaissance platform**
> *B.Tech Final Year Cybersecurity Project*

Scan-X combines **endpoint discovery + tech fingerprinting** for web targets with **source code security analysis** for GitHub repositories — two independent assessment modes, each with its own progress tracking and HTML reports.

---

## Features

### Endpoint Discovery and Fingerprinting

- **Deep Crawling** — BFS with form parsing, JS endpoint extraction, wordlist-based discovery (82 sensitive paths)
- **Technology Fingerprinting** — Detects frameworks, CMS, JS libraries, analytics tools, CDN providers
- **Categorized Reports** — HTML reports with endpoint inventory, Burp Suite test recommendations per endpoint
- **Background Job Runner** — Queued crawl sessions with real-time status tracking

### GitHub Repository Analyzer

- **44 detection rules** — Hardcoded secrets, injection vulnerabilities, XSS, SSRF, misconfigurations
- **Smart file filtering** — Skips bundled/minified JS, binary files, node_modules, build artifacts
- **Private repo support** — PAT authentication for private repos
- **Vulnerability reports** — Categorized HTML reports grouped by file, severity, and category

### Assessment System

- **Web Recon** — Target URL only; runs deep crawler + fingerprinting
- **Repository Scan** — GitHub repo URL only; runs security analysis

Each mode shows its own progress steps (Initializing → Crawling/Scanning → Complete), keeps a run history with status badges, and can generate a downloadable HTML report.

### Dashboard

- **KPI cards** — Targets, crawls, endpoints, API endpoints, login forms, completed/failed/running crawls
- **Charts** — Endpoint breakdown by source and by HTTP method
- **End-to-end coverage** — Web Recon and Repo Scan pipeline counters

### Dark UI

- **Dark theme** — Near-black base (`#0a0b0f`) with solid cards and vibrant accent colors
- **Landing page** — Hero section with feature cards
- **Assessment wizard** — Mode selection, configuration, animated progress steps, results detail view

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
│   │   └── assessments.py          # Assessment CRUD + reports
│   ├── crawler/                    # BFS crawler + form/JS/wordlist
│   ├── fingerprinter/              # Technology detection
│   ├── github_analyzer/            # Security rules + analysis
│   ├── reporting/                  # HTML report templates
│   └── scheduler/                  # Background job runner
├── frontend/
│   └── src/
│       ├── App.jsx                 # Routes
│       ├── index.css               # Dark theme
│       ├── pages/                  # Dashboard, Assess, etc.
│       ├── components/             # Sidebar
│       └── api/client.js           # Axios API client
└── database/
    └── scanx.db                    # SQLite (auto-created)
```

---

## Detection Rules

44 rules total (SEC-001 – SEC-024, VUL-001 – VUL-020):

| Category | Rule IDs | What it catches |
|----------|----------|-----------------|
| Secrets | SEC-001 – SEC-024 | AWS/GitHub/Stripe/OpenAI/Twilio keys, tokens, hardcoded passwords, private keys in source |
| Injection | VUL-001 – VUL-005 | eval/exec injection, command injection, SQL injection, SSTI, unsafe deserialization |
| XSS | VUL-006 – VUL-007 | XSS sinks (innerHTML, document.write) and unescaped output |
| SSRF | VUL-008, VUL-015 | Server-side request forgery, cloud metadata SSRF |
| Redirect | VUL-009 | Open redirect |
| Cookies & Config | VUL-010 – VUL-014, VUL-018, VUL-020 | Insecure cookies, debug mode, permissive CORS, disabled SSL verification, loose file permissions, env-loaded secrets, VCS/OS files in source |
| Crypto | VUL-016 – VUL-017 | Weak hashing, weak random number generator |
| Code Quality | VUL-019 | Security-related TODO/FIXME markers |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/targets/` | List targets |
| POST | `/targets/` | Create target |
| GET | `/crawls/` | List crawls |
| POST | `/crawls/` | Start crawl |
| POST | `/crawls/{id}/cancel` | Cancel crawl |
| GET | `/endpoints/` | List endpoints |
| GET | `/endpoints/dashboard` | Dashboard stats |
| POST | `/github/analyze` | Start GitHub scan |
| GET | `/github/analyses` | List analyses |
| GET | `/github/analyses/{id}` | Get analysis |
| GET | `/github/analyses/{id}/findings` | Get findings |
| POST | `/github/analyses/{id}/report` | Generate report |
| POST | `/assessments/web` | Start Web Recon assessment |
| POST | `/assessments/repository` | Start Repository Scan assessment |
| GET | `/assessments/` | List assessments |
| GET | `/assessments/{id}` | Get assessment |
| POST | `/assessments/{id}/report` | Generate report |
| GET | `/assessments/{id}/report/download` | Download report |
| DELETE | `/assessments/{id}` | Delete assessment |
| GET | `/api/docs` | Swagger docs |

---

## Tech Stack

- **Backend:** Python 3.13, FastAPI, SQLAlchemy, SQLite
- **Frontend:** React 18, Vite 6, React Router 6, Recharts, Lucide Icons
- **GitHub Integration:** GitHub REST API (file fetching, PAT auth)
- **Scanning:** Pattern-based rule engine (regex), BFS crawling
- **UI:** Dark theme with solid cards and vibrant accents

---

*Scan-X — B.Tech Final Year Cybersecurity Project*
