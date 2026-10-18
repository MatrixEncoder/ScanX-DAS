"""
report_generator.py — HTML report generator for GitHub repository security analysis.
"""

import base64
import os
from datetime import datetime, timezone, timedelta
from jinja2 import Environment, FileSystemLoader
from collections import defaultdict

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _logo_data_uri() -> str:
    """Return the Scan-X logo as a base64 data URI for embedding in HTML."""
    logo_path = os.path.join(TEMPLATES_DIR, "scanx-logo.png")
    if not os.path.exists(logo_path):
        return ""
    with open(logo_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{b64}"


def generate_github_report(analysis, findings, output_path):
    """Render and save an HTML GitHub analysis report."""
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    template = env.get_template("github_report.html")

    # Group findings by file
    by_file = defaultdict(list)
    for f in findings:
        by_file[f.file_path].append(f)

    # Group by category
    by_category = defaultdict(list)
    for f in findings:
        by_category[f.category].append(f)

    # Collect unique languages
    languages = sorted(set(f.language for f in findings if f.language and f.language != "unknown"))

    # File summary — sorted by finding count
    file_summary = []
    for fp, fps in sorted(by_file.items()):
        file_summary.append({
            "path": fp,
            "count": len(fps),
            "findings": fps,
        })
    file_summary.sort(key=lambda x: x["count"], reverse=True)

    context = {
        "analysis": analysis,
        "findings": findings,
        "by_file": dict(by_file),
        "by_category": dict(by_category),
        "file_summary": file_summary,
        "languages": languages,
        "total": len(findings),
        "logo_data_uri": _logo_data_uri(),
        "generated_at": (datetime.now(timezone(timedelta(hours=5, minutes=30)))).strftime("%Y-%m-%d %H:%M:%S IST"),
    }

    html = template.render(**context)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
