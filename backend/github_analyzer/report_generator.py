"""
report_generator.py — HTML report generator for GitHub repository security analysis.
"""

import os
from datetime import datetime, timezone, timedelta
from jinja2 import Environment, FileSystemLoader
from collections import defaultdict

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


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

    # Group by severity
    by_severity = defaultdict(list)
    for f in findings:
        by_severity[f.severity].append(f)

    # Collect unique languages
    languages = sorted(set(f.language for f in findings if f.language and f.language != "unknown"))

    # File summary
    file_summary = []
    for fp, fps in sorted(by_file.items()):
        file_summary.append({
            "path": fp,
            "count": len(fps),
            "max_severity": min(
                ({"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(f.severity, 99) for f in fps),
                default=99
            ),
            "findings": fps,
        })
    file_summary.sort(key=lambda x: x["max_severity"])

    context = {
        "analysis": analysis,
        "findings": findings,
        "by_file": dict(by_file),
        "by_category": dict(by_category),
        "by_severity": dict(by_severity),
        "file_summary": file_summary,
        "languages": languages,
        "total": len(findings),
        "generated_at": (datetime.now(timezone(timedelta(hours=5, minutes=30)))).strftime("%Y-%m-%d %H:%M:%S IST"),
    }

    html = template.render(**context)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Copy logo to reports directory for local HTML viewing
    logo_src = os.path.join(TEMPLATES_DIR, "logo.png")
    logo_dst = os.path.join(os.path.dirname(output_path), "logo.png")
    if os.path.exists(logo_src) and not os.path.exists(logo_dst):
        import shutil
        shutil.copy2(logo_src, logo_dst)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
