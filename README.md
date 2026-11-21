# Scan-X

> **Endpoint Discovery & Security Assessment Platform**  
> *B.Tech Final Year Cybersecurity Project — 2026*

Scan-X combines **automated endpoint discovery + technology fingerprinting** for web targets with **source code security scanning** for GitHub repositories. Designed for security analysts and penetration testers, it provides deep reconnaissance, Burp Suite testing recommendations, and vulnerability detection with exportable HTML reports.

---

## 🚀 Key Features

### 1. Web Reconnaissance & Endpoint Discovery
- **Deep BFS Web Crawler**: Discovers internal links, extracts HTML forms and parameters, analyzes inline and external JavaScript files for hidden API routes.
- **Sensitive Path Probing**: Automated checks against 82 sensitive paths and administrative endpoints.
- **Technology Fingerprinting**: Identifies backend frameworks, CMS platforms, servers, JavaScript libraries, and security headers.
- **Pentest Burp Suite Mapping**: Automatically generates specific manual testing recommendations (SQLi, XSS, IDOR, SSRF, Mass Assignment, Auth Bypass) for every discovered endpoint.

### 2. GitHub Repository Security Analyzer
- **44 Security Rules Engine**:
  - **Secrets (SEC-001 – SEC-024)**: Hardcoded API keys, tokens (AWS, GitHub, Stripe, OpenAI, Slack, JWT), private keys, and database credentials.
  - **Vulnerabilities & Injections (VUL-001 – VUL-020)**: Command injection, SQL injection, unsafe deserialization, SSTI, SSRF, DOM/Reflected XSS sinks, CORS misconfigurations, weak cryptography, and debug flag exposures.
- **REST API-Driven Scanning**: Direct Git tree inspection via GitHub REST API without requiring local repo cloning; supports Personal Access Tokens (PAT) for private repositories.
- **Intelligent Noise Filtering**: Skips build artifacts, minified files, lockfiles, and dependencies (`node_modules`, `vendor`, `dist`, etc.).

### 3. Unified Assessment Wizard
- **Web Recon Mode**: Launch target URL crawling and fingerprinting with live status updates.
- **Repository Scan Mode**: Connect to GitHub repos and branch targets with real-time progress indicators.
- **Downloadable Reports**: Clean, standalone HTML reports for both Web Recon and Repository Scans with categorized findings and executive metrics.

### 4. Interactive Dashboard & Analytics
- **Live Discovery Metrics**: Targets, Crawls, Discovered Endpoints, API routes, and Login forms.
- **Visual Analytics**: Interactive Recharts breakdown of Endpoint Sources (Links, Forms, JS, Wordlists) and HTTP Methods (GET, POST, etc.).
- **Modern Dark UI**: Cybersecurity dark aesthetics, status indicators, and clean table navigation.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+ (tested on Python 3.13), FastAPI, SQLAlchemy (SQLite ORM), Uvicorn, Jinja2, BeautifulSoup4, Requests
- **Frontend**: React 18, Vite 6, React Router DOM 6, Recharts, Lucide React, Axios
- **Database**: SQLite (`database/scanx.db`)

---

## ⚡ Quick Start

### Prerequisites
- **Python 3.10+** (Python 3.13 recommended)
- **Node.js 18+** & npm

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/your-username/Scan-X.git
cd Scan-X

# Install Python backend requirements
pip install -r backend/requirements.txt

# Install frontend dependencies and build production assets
cd frontend
npm install
npm run build
cd ..
```

### 2. Run Scan-X

You can launch the full application (FastAPI serves both the REST API and the built React frontend) with a single command:

```bash
python run.py
```

Open your browser at: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

*(Optional Developer Mode: To run the Vite hot-reloading dev server on port 5173, run `npm run dev` inside `frontend/` while `run.py` is running on port 8000.)*

---

## 📂 Project Structure

```
Scan-X/
├── run.py                          # Unified server startup script
├── verify.py                       # Automated verification test script
├── backend/
│   ├── main.py                     # FastAPI app, middleware & SPA router
│   ├── database.py                 # SQLite engine & session management
│   ├── models.py                   # SQLAlchemy ORM models
│   ├── schemas.py                  # Pydantic v2 validation models
│   ├── api/
│   │   ├── targets.py              # Target CRUD API
│   │   ├── crawls.py               # Web crawl management & job triggers
│   │   ├── endpoints.py            # Discovered endpoint queries & dashboard stats
│   │   ├── reports.py              # Crawl report generation & downloads
│   │   ├── github_api.py           # GitHub repository scanning & findings API
│   │   └── assessments.py          # Unified assessment pipeline & reports
│   ├── crawler/
│   │   ├── deep_crawler.py         # Priority BFS web crawler
│   │   ├── form_parser.py          # HTML form & link parser
│   │   ├── js_analyzer.py          # JavaScript file & inline endpoint extractor
│   │   └── wordlist.py             # 82 sensitive path patterns
│   ├── fingerprinter/
│   │   └── tech_detect.py          # Framework, CMS & server fingerprinting
│   ├── github_analyzer/
│   │   ├── analyzer.py             # Code scanner orchestration
│   │   ├── github_client.py        # GitHub REST client & tree traversal
│   │   ├── security_rules.py       # 44 static analysis regex rules
│   │   └── report_generator.py     # HTML vulnerability report generator
│   ├── reporting/
│   │   ├── endpoint_report.py      # HTML endpoint report generator & Burp mapper
│   │   └── templates/              # Jinja2 report templates & assets
│   └── scheduler/
│       └── job_runner.py           # Background task execution pipeline
├── frontend/
│   ├── dist/                       # Built frontend assets (served by FastAPI)
│   ├── src/
│   │   ├── App.jsx                 # Application routes & layout
│   │   ├── index.css               # Dark theme styles & UI design system
│   │   ├── api/client.js           # Axios API bindings
│   │   ├── components/             # Reusable UI components (Sidebar, etc.)
│   │   └── pages/
│   │       ├── Landing.jsx         # Project landing page
│   │       ├── Dashboard.jsx       # Real-time metrics & charts
│   │       ├── Assess.jsx          # Dual-mode assessment runner
│   │       ├── Targets.jsx         # Web application targets manager
│   │       ├── Crawls.jsx          # Crawl sessions manager
│   │       ├── Endpoints.jsx       # Discovered endpoints inspector
│   │       ├── GithubScan.jsx      # GitHub analysis manager & finding viewer
│   │       └── Reports.jsx         # Generated reports viewer & exporter
│   ├── package.json
│   └── vite.config.js              # Vite config with API proxy definitions
└── database/
    ├── scanx.db                    # SQLite database (auto-initialized)
    └── reports/                    # Generated HTML reports storage
```

---

## 🔍 Detection Rules Summary

The repository analyzer features 44 curated rules categorized by severity and attack surface:

| Category | Rule Count | Identifiers | Description |
|---|---|---|---|
| **Secrets & Keys** | 24 | `SEC-001` – `SEC-024` | AWS keys, GitHub tokens, Slack webhooks, Stripe keys, OpenAI keys, private keys, passwords, database URLs |
| **Command & Code Injection** | 5 | `VUL-001` – `VUL-005` | Unsafe `eval()`, `exec()`, shell command execution, SQL query concatenation, SSTI, unsafe deserialization |
| **Cross-Site Scripting (XSS)** | 2 | `VUL-006` – `VUL-007` | Dangerous DOM sinks (`innerHTML`, `outerHTML`, `document.write`), unescaped template output |
| **SSRF & Open Redirects** | 3 | `VUL-008`, `VUL-009`, `VUL-015` | Server-side request forgery, unvalidated HTTP redirects, cloud metadata endpoints (169.254.169.254) |
| **Configuration & Misconfig** | 7 | `VUL-010` – `VUL-014`, `VUL-018`, `VUL-020` | Insecure cookie flags, debug mode enabled, wildcard CORS, SSL verification disabled, `.env`/VCS exposure |
| **Cryptographic Weaknesses** | 2 | `VUL-016` – `VUL-017` | Deprecated hashes (`MD5`, `SHA1`), non-cryptographic PRNGs (`random.random`) |
| **Code Smells** | 1 | `VUL-019` | Security-relevant `TODO`, `FIXME`, `HACK` comments |

---

## 🌐 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health status check |
| `GET` | `/api/docs` | Interactive Swagger / OpenAPI documentation |
| `GET` | `/targets/` | List all registered target applications |
| `POST` | `/targets/` | Register a new web target |
| `DELETE` | `/targets/{id}` | Delete target and associated crawl data |
| `GET` | `/crawls/` | List all web crawl sessions |
| `POST` | `/crawls/` | Launch background crawl on a target |
| `POST` | `/crawls/{id}/cancel` | Cancel an in-progress crawl session |
| `GET` | `/endpoints/` | Search & filter discovered endpoints (by source, API status, URL) |
| `GET` | `/endpoints/dashboard` | Aggregated dashboard KPI metrics and chart counts |
| `POST` | `/reports/{crawl_id}/generate` | Generate HTML endpoint discovery report |
| `GET` | `/reports/{crawl_id}/download/{format}` | Download generated report |
| `POST` | `/github/analyze` | Start repository security analysis |
| `GET` | `/github/analyses` | List all repository scans |
| `GET` | `/github/analyses/{id}/findings` | Retrieve discovered findings filtered by severity |
| `POST` | `/github/analyses/{id}/report` | Generate HTML repository security report |
| `GET` | `/github/analyses/{id}/report/download` | Download repository analysis HTML report |
| `POST` | `/assessments/web` | Launch Web Recon assessment |
| `POST` | `/assessments/repository` | Launch Repository Scan assessment |
| `GET` | `/assessments/` | List assessment history |
| `POST` | `/assessments/{id}/report` | Generate assessment HTML report |
| `GET` | `/assessments/{id}/report/download` | Download assessment HTML report |

---

## 🎓 Academic Project Information

- **Degree**: Bachelor of Technology (B.Tech)
- **Specialization**: Computer Science & Engineering / Information Technology / Cybersecurity
- **Project Title**: Scan-X — Endpoint Discovery & Security Assessment Platform
- **Year**: 2026
