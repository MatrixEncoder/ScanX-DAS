# Scan-X: An Integrated Crawler and SAST Security Analysis Tool

> **Bachelor of Technology in Computer Science & Engineering**  
> *Final Year Major Project Report Implementation (2026)*  
> *Department of Computer Science & Engineering, Madan Mohan Malaviya University of Technology, Gorakhpur*

---

## 📌 Executive Summary & Abstract

Modern web application security typically forces security engineers and penetration testers to operate with fragmented tooling. Dynamic Application Security Testing (DAST) utilities probe runtime web endpoints from the outside, while Static Application Security Testing (SAST) tools analyze source code repositories for security flaws. This operational divide requires security teams to juggle multiple disconnected interfaces, inconsistent reporting formats, and disparate CLI tools.

**Scan-X** bridges this operational gap by consolidating two essential cybersecurity assessment pillars into a single, unified platform:

1. **Dynamic Web Reconnaissance & Endpoint Discovery**: An intelligent breadth-first crawler that parses HTML anchor tags, extracts form actions/parameters, extracts routes from inline and external JavaScript, probes 82 sensitive path patterns, fingerprints backend technologies, and automatically maps actionable **Burp Suite manual penetration testing recommendations**.
2. **GitHub Repository Static Code Security Analysis**: A direct REST API-driven SAST scanner that evaluates source files against **44 pattern-based security detection rules** (identifying hardcoded secrets, injection sinks, cross-site scripting vulnerabilities, SSRF, open redirects, and security misconfigurations) without requiring local Git clones.

Both assessment workflows run independently through asynchronous background workers and export self-contained, presentation-ready **HTML penetration testing reports**.

---

## 🎯 Project Objectives

- **Deep Web Crawling**: Implement a configurable BFS spider (link extraction, form parsing, inline/external JavaScript analysis) with intelligent priority scoring.
- **Sensitive Path Discovery**: Automated probing against an 82-entry sensitive path wordlist (`/.env`, `/admin`, `/api`, `/backup`, `/phpinfo`, etc.).
- **Technology Fingerprinting**: Identify server software, programming runtimes, web frameworks (Django, Flask, Express, Laravel), CMS platforms, and CDN providers via response headers and page signatures.
- **Actionable Burp Suite Guidance**: Generate context-specific testing instructions (Repeater/Intruder workflows, parameter tampering, SQLi/XSS/SSRF/IDOR test payloads) for each discovered endpoint.
- **REST-Driven Static Code Analysis**: Traverse Git trees via the GitHub REST API using Personal Access Tokens (PAT) for private repositories or unauthenticated access for public repositories.
- **Rule-Based Vulnerability Engine**: Apply 44 detection rules with regex pattern filtering and noise suppression (skipping lockfiles, node_modules, minified chunks, build artifacts).
- **Consolidated Dashboard & Reporting**: Offer an interactive dark glassmorphism dashboard (KPI metrics, source distribution donuts, HTTP method bar charts) and standalone HTML report generation with embedded base64 assets.
- **Future Extensibility**: Establish modular software architecture and standardized data schemas enabling future integrations with external scanners (Wapiti, Nuclei, Burp Suite) and automated CI/CD pipelines.

---

## 🏗️ System Architecture & Database Design

Scan-X is structured across five decoupled layers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER (React 18 + Vite 6)               │
│  Landing Page  │  Dashboard  │  Assess Wizard  │  Targets  │  Reports  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Axios HTTP / REST API
┌───────────────────────────────────▼────────────────────────────────────┐
│                    API ROUTING LAYER (FastAPI Backend)                 │
│ /targets  │  /crawls  │  /endpoints  │  /reports  │  /github  │ /assess │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Async BackgroundTasks Dispatch
┌───────────────────────────────────▼────────────────────────────────────┐
│                             CORE ENGINES                               │
│  Deep BFS Crawler   │  Tech Fingerprinter  │  GitHub REST SAST Engine  │
│  (Links, Forms, JS) │  (Headers & Signatures) (44 Detection Rules)     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SQLAlchemy 2.0 ORM
┌───────────────────────────────────▼────────────────────────────────────┐
│                       PERSISTENCE LAYER (SQLite)                       │
│                            database/scanx.db                           │
└────────────────────────────────────────────────────────────────────────┘
```

### Relational Database Schema (7 Interconnected Tables)

The persistence layer is managed via SQLAlchemy ORM in `backend/models.py`:

| Table Name | Entity Description | Key Attributes | Relationships |
|---|---|---|---|
| `targets` | Registered web applications | `id`, `name`, `base_url`, `notes`, `created_at` | `1:N` with `crawl_sessions`, `1:N` with `endpoints` |
| `crawl_sessions` | Web crawling audit sessions | `id`, `target_id`, `status`, `max_depth`, `max_pages`, `total_endpoints`, `crawl_duration`, `pages_crawled`, `forms_found`, `tech_fingerprint`, `created_at`, `started_at`, `completed_at` | `N:1` with `targets`, `1:N` with `endpoints`, `1:N` with `reports` |
| `endpoints` | Discovered URLs and forms | `id`, `target_id`, `crawl_id`, `url`, `methods`, `status_code`, `content_type`, `title`, `parameters`, `form_count`, `source`, `depth`, `is_api`, `has_login_form`, `discovered_at` | `N:1` with `targets`, `N:1` with `crawl_sessions` |
| `reports` | Generated audit reports | `id`, `crawl_id`, `format` (`html`, `github_html`, etc.), `filepath`, `generated_at` | `N:1` with `crawl_sessions` |
| `github_analyses` | Repository scan jobs | `id`, `repo_url`, `repo_name`, `branch`, `status`, `total_files`, `files_scanned`, `total_findings`, severity counts, `analysis_duration`, `created_at` | `1:N` with `github_findings` |
| `github_findings` | Individual code vulnerabilities | `id`, `analysis_id`, `file_path`, `line_number`, `end_line`, `language`, `rule_id`, `severity`, `category`, `title`, `evidence`, `recommendation` | `N:1` with `github_analyses` |
| `assessments` | Unified assessment tracking | `id`, `assessment_type` (`WEB_RECON` / `REPOSITORY_SCAN`), `status`, `target_url`, `repo_url`, `pat`, `branch`, `crawl_id`, `analysis_id`, `created_at` | Foreign keys to `crawl_sessions` and `github_analyses` |

---

## 🔍 Security Detection Rules (44 Rules)

Scan-X embeds 44 static analysis detection rules in `backend/github_analyzer/security_rules.py` categorized by attack vector and severity:

| Identifier Range | Security Category | Target Vulnerabilities & Pattern Highlights | Max Severity |
|---|---|---|---|
| **SEC-001 – SEC-024** | **Secrets & Credentials** | AWS Access & Secret Keys, GitHub Personal Access Tokens, Stripe Secret Keys, OpenAI API Keys, Google API Keys, Twilio Auth Tokens, Slack Webhook URLs, Private RSA/DSA/EC Keys, Generic Passwords in config/source, JWT Secret Strings, Database Connection URIs | **Critical** |
| **VUL-001 – VUL-005** | **Code & Query Injection** | Dangerous `eval()` / `exec()` calls, Shell Command Injection (`subprocess`, `child_process.exec`, `os.system`), SQL Query String Concatenation, Server-Side Template Injection (SSTI in Jinja2, Twig, ERB), Insecure Deserialization (`pickle.loads`, `yaml.unsafe_load`, `ObjectInputStream`) | **Critical** |
| **VUL-006 – VUL-007** | **Cross-Site Scripting (XSS)** | Dangerous client-side DOM sinks (`innerHTML`, `outerHTML`, `document.write`), Unescaped template output (`v-html`, `dangerouslySetInnerHTML`) | **High** |
| **VUL-008, VUL-015** | **SSRF & Cloud Metadata** | Server-Side Request Forgery sinks (`requests.get(user_var)`, `axios(url)`), Cloud Metadata Service IP probes (`169.254.169.254` access) | **High** |
| **VUL-009** | **Open Redirection** | Unvalidated URL redirection parameters and `window.location` assignments | **Medium** |
| **VUL-010 – VUL-014** | **Security Misconfiguration** | Insecure Cookie Flags (missing `HttpOnly`, `Secure`), Framework Debug Modes (`DEBUG = True`, `app.debug`), Wildcard CORS (`Access-Control-Allow-Origin: *`), Disabled SSL Verification (`verify=False`, `rejectUnauthorized: false`), Loose File Permissions (`chmod 0777`) | **High** |
| **VUL-016 – VUL-017** | **Weak Cryptography** | Deprecated hashing algorithms (`MD5`, `SHA1` used for sensitive hashing), Non-cryptographic Pseudo-Random Number Generators (`random.random()`, `Math.random()`) | **Medium** |
| **VUL-018, VUL-020** | **Exposure & Information Leakage** | Committed environment variable files (`.env`), Leaked Version Control & OS metadata files (`.git`, `.DS_Store`) | **Medium** |
| **VUL-019** | **Code Quality & Technical Debt** | Security-relevant `TODO`, `FIXME`, and `HACK` comments indicating incomplete access controls | **Low** |

---

## 🛠️ Burp Suite Penetration Testing Recommendation Matrix

Every endpoint identified during dynamic crawling is automatically parsed and mapped to tailored manual testing instructions:

| Discovered Endpoint Characteristic | Burp Suite Tool | Target Vulnerability Class | Recommended Testing Procedure |
|---|---|---|---|
| **Query & Body Parameters (`?q=`, `id=`)** | Repeater & Intruder | SQL Injection & Parameter Tampering | Inject `' OR 1=1--`, `UNION SELECT`, type boundary values, negative quantities, and format string characters. |
| **Input Rendered in Page / Response** | Repeater | Cross-Site Scripting (Reflected/Stored) | Test `<script>alert(1)</script>`, `<img src=x onerror=alert(1)>`, and context-specific attribute break-out payloads. |
| **POST / PUT Endpoints** | Repeater | Mass Assignment & Parser Differential | Inject elevated parameter keys (`admin: true`, `role: "admin"`); switch `Content-Type` between JSON, form-data, and XML. |
| **API Endpoints (`/api/`, `/v1/`, `/v2/`)** | Repeater & Intruder | Broken Object Level Auth (BOLA / IDOR) | Strip Authorization Bearer headers, swap tokens between testing accounts, and fuzz numeric object identifiers. |
| **Authentication Forms (Password Fields)** | Intruder & Repeater | Brute Force & Session Fixation | Test common credential dictionaries, evaluate cookie security flags (`SameSite`, `HttpOnly`, `Secure`), and test token entropy. |
| **File Upload Endpoints (`/upload`)** | Repeater | File Upload Bypass & Zip Slip | Test double extensions (`.php.jpg`), null byte injection, image magic byte tampering, and path traversal in `filename`. |
| **Redirect Endpoints (`/redirect`, `next=`)** | Repeater | Open URL Redirection | Test external URL injection using payloads such as `//attacker.com`, `/\/attacker.com`, and encoded delimiters. |

---

## 💻 Tech Stack & Dependencies

- **API Server & Routing**: Python 3.13, FastAPI (asynchronous ASGI framework), Uvicorn
- **ORM & Storage**: SQLAlchemy 2.0+ (Declarative mapping), SQLite 3
- **Crawling & HTML Extraction**: Requests, BeautifulSoup4 (lxml parsing), urllib3
- **Reporting Engine**: Jinja2 (HTML templating with auto-escaping)
- **Frontend SPA**: React 18, Vite 6, React Router DOM 6
- **UI Design System**: Custom Dark Glassmorphism CSS, Lucide React (vector iconography)
- **Data Visualization**: Recharts (Pie/Donut charts, Bar charts, ResponsiveContainers)
- **HTTP Client**: Axios (configured with automated Vite proxy routing)

---

## 🚀 Installation & Quick Start

### 1. Prerequisites
- **Python 3.10+** (Python 3.13 recommended)
- **Node.js 18+** & npm

### 2. Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/your-username/Scan-X.git
cd Scan-X

# Optional: Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 3. Install Backend Dependencies
```bash
pip install -r backend/requirements.txt
```

### 4. Build Frontend Assets
FastAPI directly serves the built React single-page application from `frontend/dist/`. Build production assets with:
```bash
cd frontend
npm install
npm run build
cd ..
```

### 5. Launch the Platform
Start the unified application:
```bash
python run.py
```

Access Scan-X in your browser at: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

*(For active frontend development with hot-module reloading, run `npm run dev` in `frontend/` on port 5173. The proxy in `vite.config.js` will automatically redirect API calls to port 8000.)*

---

## 📁 Repository Directory Layout

```
Scan-X/
├── run.py                          # Unified server startup script (FastAPI on 8000)
├── README.md                       # Comprehensive project documentation
├── package.json                    # Workspace dependencies
├── ScanX_Project_Report.docx       # Complete academic project report
├── mmmut-logo.png                  # University crest
├── scanx-logo.png                  # Scan-X brand mark
├── backend/
│   ├── main.py                     # FastAPI application, CORS & SPA route handler
│   ├── database.py                 # SQLite engine, DeclarativeBase & sessionmaker
│   ├── models.py                   # 7 SQLAlchemy ORM models
│   ├── schemas.py                  # Pydantic v2 validation models
│   ├── requirements.txt            # Python package requirements
│   ├── api/
│   │   ├── targets.py              # Target application CRUD endpoints
│   │   ├── crawls.py               # Crawl session controls & cancellation
│   │   ├── endpoints.py            # Endpoint inventory, search & dashboard metrics
│   │   ├── reports.py              # Crawl HTML report generation and streaming
│   │   ├── github_api.py           # GitHub scan triggers, findings & report API
│   │   └── assessments.py          # Unified Web Recon & Repo Scan pipelines
│   ├── crawler/
│   │   ├── deep_crawler.py         # Priority-queue BFS crawler engine
│   │   ├── form_parser.py          # HTML form parameter & link extractor
│   │   ├── js_analyzer.py          # JavaScript regex route extractor
│   │   └── wordlist.py             # 82 sensitive path probing wordlist
│   ├── fingerprinter/
│   │   └── tech_detect.py          # Framework, server & library detection rules
│   ├── github_analyzer/
│   │   ├── analyzer.py             # GitHub REST API scanner orchestrator
│   │   ├── github_client.py        # Git tree & file contents API client
│   │   ├── security_rules.py       # 44 static security analysis regex rules
│   │   ├── report_generator.py     # HTML report compiler for repository audits
│   │   └── templates/              # Repository report Jinja2 templates
│   ├── reporting/
│   │   ├── endpoint_report.py      # Burp Suite recommendation mapper
│   │   └── templates/              # HTML discovery report Jinja2 templates
│   └── scheduler/
│       └── job_runner.py           # Asynchronous crawl execution pipeline
├── frontend/
│   ├── dist/                       # Production build output (served by FastAPI)
│   ├── package.json                # React 18, Vite, Lucide & Recharts dependencies
│   ├── vite.config.js              # Vite server & API proxy routing configuration
│   └── src/
│       ├── App.jsx                 # Client-side routes & layout structure
│       ├── index.css               # Dark theme design system & CSS variables
│       ├── api/client.js           # Axios API functions
│       ├── components/
│       │   └── Sidebar.jsx         # Navigation sidebar component
│       └── pages/
│           ├── Landing.jsx         # Project hero landing page
│           ├── Dashboard.jsx       # Analytics, KPI metrics & visual charts
│           ├── Assess.jsx          # Dual-mode assessment runner
│           ├── Targets.jsx         # Target application manager
│           ├── Crawls.jsx          # Crawl session manager & execution triggers
│           ├── Endpoints.jsx       # Discovered endpoints inspector
│           ├── GithubScan.jsx      # GitHub repository security scanner
│           └── Reports.jsx         # Report generator and download center
└── database/
    ├── scanx.db                    # SQLite database (auto-created on startup)
    └── reports/                    # Generated standalone HTML audit reports
```

---

## ⚡ API Reference

| Method | Endpoint Path | Functionality Description |
|---|---|---|
| `GET` | `/api/health` | Health check endpoint returning API operational status |
| `GET` | `/api/docs` | Interactive Swagger / OpenAPI UI documentation |
| `GET` | `/targets/` | List all registered target applications |
| `POST` | `/targets/` | Register a new target URL and metadata |
| `DELETE` | `/targets/{id}` | Delete a target and cascade delete all associated crawls and endpoints |
| `GET` | `/crawls/` | List all crawl sessions ordered by creation date |
| `POST` | `/crawls/` | Launch background BFS crawling session on a target |
| `POST` | `/crawls/{id}/cancel` | Cancel an active queued or running crawl |
| `GET` | `/endpoints/` | Query endpoints filtered by `crawl_id`, `source`, `is_api`, or `search` |
| `GET` | `/endpoints/dashboard` | Retrieve aggregated dashboard counts, charts, and crawl histories |
| `POST` | `/reports/{crawl_id}/generate` | Compile Jinja2 HTML endpoint discovery report with Burp recommendations |
| `GET` | `/reports/{crawl_id}/download/{format}` | Download generated HTML endpoint report |
| `POST` | `/github/analyze` | Launch asynchronous security scan on a GitHub repository URL |
| `GET` | `/github/analyses` | List all repository analysis jobs |
| `GET` | `/github/analyses/{id}/findings` | Retrieve findings for a scan filtered by `severity` or `category` |
| `POST` | `/github/analyses/{id}/report` | Generate standalone HTML repository vulnerability report |
| `GET` | `/github/analyses/{id}/report/download` | Download repository analysis HTML report |
| `POST` | `/assessments/web` | Launch a Web Reconnaissance assessment job |
| `POST` | `/assessments/repository` | Launch a Repository Security Analysis assessment job |
| `GET` | `/assessments/` | List assessment execution history |
| `POST` | `/assessments/{id}/report` | Generate assessment HTML report |
| `GET` | `/assessments/{id}/report/download` | Download assessment HTML report |
| `DELETE` | `/assessments/{id}` | Delete assessment record |

---

## 🔬 Benchmark Performance & System Responsiveness

Under single-user evaluation on standard local test hardware (Intel Core i7, 16GB RAM, Windows 11, Python 3.13), Scan-X demonstrates high operational throughput:

- **Target Deep Crawling**: Typical web application targets crawled within **5 – 15 seconds** (depth: 2, BFS spider with form & JS extraction).
- **Sensitive Path Probing**: 82 sensitive path probes completed in **< 3 seconds**.
- **GitHub REST Tree Traversal**: Average repository trees (50–100 files) fetched and inspected in **< 5 seconds** via REST APIs.
- **Rule Matching Latency**: Evaluation of all 44 regex security rules across fetched files takes **< 200 ms**.
- **Report Generation**: Standalone HTML report rendering with embedded base64 logos completes in **< 1.5 seconds**.
- **API Response Latency**: Core FastAPI JSON endpoints respond with P95 latency of **< 100 ms** on localhost.
- **Idle Memory Consumption**: Background server footprint sits at **~65 MB RAM**.

---

## 🔮 Future Enhancements

As documented in Chapter 6 of the project report, potential future milestones for the platform include:
- **Crawlee Engine Integration**: Upgrading the spider to utilize Crawlee for Python to handle browser-rendering (Playwright), session rotation, and anti-bot evasion.
- **Proposed AI-Assisted Page Analysis**: Exploring ScrapeGraph-AI or local LLMs to intelligently extract unstructured API routes and navigation flows from complex client-rendered web applications.
- **Direct Security Tool Chaining**: Integrating active CLI execution hooks for utilities such as Nmap, Nuclei, and SQLMap.
- **Automated CI/CD Pipeline Integration**: Exposing GitHub Actions and Jenkins runner plugins to trigger security gates on pull requests.

---

## 👨‍🎓 Project Credits & Academic Attribution

- **Institution**: Department of Computer Science & Engineering, Madan Mohan Malaviya University of Technology, Gorakhpur
- **Degree**: Bachelor of Technology (B.Tech) in Computer Science & Engineering
- **Academic Session**: 2025 – 2026
- **Project Group ID**: G60
- **Supervisor**: Dr. Birendra Kumar Sharma, Associate Professor
- **Student Contributors**:
  - Suryansh Srivastava (Roll No: 2023021161)
  - Ashutosh Sharma (Roll No: 2023021222)
  - Vivek Maurya (Roll No: 2023021168)
