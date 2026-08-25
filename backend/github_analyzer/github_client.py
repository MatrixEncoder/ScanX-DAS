"""
github_client.py — GitHub API client for fetching repository files.

Uses the GitHub REST API to list and read files from a repository.
Supports private repos via Personal Access Token (PAT).
"""

import re
import os
import shutil
import logging
import subprocess
import tempfile
import base64
from typing import List, Optional
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)

# Files/dirs to always skip
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", ".nuxt", "vendor", "target",
    ".idea", ".vscode", ".gradle", "coverage", ".tox", "eggs",
    "bower_components", "jspm_packages", ".eggs",
    "static", "assets", "media", "public",
}
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".bmp",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".zip", ".tar", ".gz", ".rar", ".7z", ".bz2",
    ".mp3", ".mp4", ".avi", ".mov", ".wmv",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".lock", ".min.js", ".min.css",
    ".pyc", ".pyo", ".class", ".o", ".so", ".dll",
    ".db", ".sqlite", ".sqlite3",
    ".map", ".chunk.js", ".chunk.css",
}

# Patterns for bundled/hashed filenames (React, Vue, Webpack outputs)
SKIP_NAME_PATTERNS = [
    r"^[a-z]+\.[a-f0-9]{6,}\.(js|css)$",   # main.8aef5b22.js
    r"^[a-z]+\.[a-f0-9]{6,}\.chunk\.(js|css)$",
    r"^vendors\.[a-f0-9]{6,}\.(js|css)$",
    r"^bundle\.[a-f0-9]{6,}\.(js|css)$",
    r"^app\.[a-f0-9]{6,}\.(js|css)$",
    r"^main\.[a-f0-9]{6,}\.(js|css)$",
]

MINIFIED_LINE_THRESHOLD = 10000  # lines in <100 chars = minified


def _should_skip_file(file_path: str, name: str, content: str = None) -> bool:
    """Check if a file should be skipped (bundled, minified, or non-source)."""
    import os
    parts = file_path.replace("\\", "/").split("/")
    if any(p in SKIP_DIRS for p in parts):
        return True
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if ext.lower() in SKIP_EXTENSIONS:
        return True
    for pattern in SKIP_NAME_PATTERNS:
        if re.match(pattern, name, re.IGNORECASE):
            return True
    if content:
        lines = content.split("\n")
        if len(lines) < 50:
            long_lines = sum(1 for l in lines if len(l) > 300)
            if long_lines > len(lines) * 0.5:
                return True
        if len(lines) < 20:
            avg_len = sum(len(l) for l in lines) / max(len(lines), 1)
            if avg_len > 500:
                return True
    return False
MAX_FILE_SIZE = 500_000  # 500KB


@dataclass
class RepoFile:
    """A file from a GitHub repository."""
    path: str
    name: str
    size: int
    sha: str
    content: str = ""
    language: str = ""


def parse_github_url(url: str) -> tuple:
    """
    Parse a GitHub URL into (owner, repo).
    Accepts:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - github.com/owner/repo
      - owner/repo
    """
    url = url.strip().rstrip("/")
    url = re.sub(r"\.git$", "", url)
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"^github\.com/", "", url)
    parts = url.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {url}. Expected format: owner/repo")
    return parts[0], parts[1]


def detect_language(path: str) -> str:
    """Detect programming language from file extension."""
    ext_map = {
        ".py": "python", ".js": "javascript", ".jsx": "javascript",
        ".ts": "typescript", ".tsx": "typescript",
        ".java": "java", ".kt": "kotlin", ".scala": "scala",
        ".go": "go", ".rs": "rust", ".c": "c", ".cpp": "cpp",
        ".cs": "csharp", ".rb": "ruby", ".php": "php",
        ".swift": "swift", ".dart": "dart",
        ".sh": "shell", ".bash": "shell", ".zsh": "shell",
        ".yml": "yaml", ".yaml": "yaml",
        ".json": "json", ".xml": "xml", ".toml": "toml",
        ".sql": "sql", ".graphql": "graphql", ".gql": "graphql",
        ".html": "html", ".htm": "html", ".css": "css",
        ".scss": "css", ".less": "css",
        ".env": "env", ".ini": "ini", ".cfg": "config",
        ".tf": "terraform", ".hcl": "terraform",
        ".dockerfile": "docker", ".dockerignore": "docker",
        ".md": "markdown", ".txt": "text",
    }
    path_lower = path.lower()
    for ext, lang in ext_map.items():
        if path_lower.endswith(ext):
            return lang
    if "dockerfile" in path_lower:
        return "docker"
    if "makefile" in path_lower:
        return "makefile"
    if "rakefile" in path_lower:
        return "ruby"
    return "unknown"


class GithubClient:
    """
    Fetch files from a GitHub repository using the REST API.
    Supports both public and private repos (via PAT).
    """

    def __init__(self, token: Optional[str] = None):
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ScanX-GithubAnalyzer/1.0",
        })
        if token:
            self.session.headers["Authorization"] = f"token {token}"

    def get_repo_info(self, owner: str, repo: str) -> dict:
        """Get repository metadata."""
        resp = self.session.get(f"{self.base_url}/repos/{owner}/{repo}")
        resp.raise_for_status()
        return resp.json()

    def list_files(self, owner: str, repo: str, path: str = "", branch: str = "main") -> List[dict]:
        """
        Recursively list all files in a repo using the Git tree API.
        Returns flat list of file dicts with path, size, sha.
        """
        # Get the full git tree (recursive)
        try:
            resp = self.session.get(
                f"{self.base_url}/repos/{owner}/{repo}/git/trees/{branch}",
                params={"recursive": "1"}
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"[GithubClient] Failed to get tree for {branch}, trying default branch: {e}")
            repo_info = self.get_repo_info(owner, repo)
            default_branch = repo_info.get("default_branch", "main")
            resp = self.session.get(
                f"{self.base_url}/repos/{owner}/{repo}/git/trees/{default_branch}",
                params={"recursive": "1"}
            )
            resp.raise_for_status()
            data = resp.json()

        files = []
        for item in data.get("tree", []):
            if item.get("type") != "blob":
                continue
            file_path = item["path"]

            # Skip directories and bad extensions
            parts = file_path.split("/")
            if any(p in SKIP_DIRS for p in parts):
                continue
            name = parts[-1]
            ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
            if ext.lower() in SKIP_EXTENSIONS:
                continue
            if item.get("size", 0) > MAX_FILE_SIZE:
                continue
            # Skip bundled/hashed filenames
            skip = False
            for pattern in SKIP_NAME_PATTERNS:
                if re.match(pattern, name, re.IGNORECASE):
                    skip = True
                    break
            if skip:
                continue

            files.append({
                "path": file_path,
                "name": name,
                "size": item.get("size", 0),
                "sha": item.get("sha", ""),
            })

        logger.info(f"[GithubClient] Listed {len(files)} files from {owner}/{repo}")
        return files

    def get_file_content(self, owner: str, repo: str, file_path: str) -> Optional[str]:
        """Fetch the content of a single file."""
        try:
            resp = self.session.get(
                f"{self.base_url}/repos/{owner}/{repo}/contents/{file_path}"
            )
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, dict) and data.get("content"):
                content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                return content
            elif isinstance(data, dict) and data.get("download_url"):
                # Fallback to download URL for large files
                raw_resp = self.session.get(data["download_url"])
                raw_resp.raise_for_status()
                return raw_resp.text
        except Exception as e:
            logger.debug(f"[GithubClient] Could not fetch {file_path}: {e}")
        return None

    def fetch_repo_files(self, owner: str, repo: str, branch: str = "main") -> List[RepoFile]:
        """
        Fetch all readable files from a repo.
        Returns list of RepoFile with content populated.
        """
        file_list = self.list_files(owner, repo, branch=branch)
        result = []

        for fi in file_list:
            content = self.get_file_content(owner, repo, fi["path"])
            if content is None:
                continue
            # Skip binary-looking content
            if "\x00" in content:
                continue
            result.append(RepoFile(
                path=fi["path"],
                name=fi["name"],
                size=fi["size"],
                sha=fi["sha"],
                content=content,
                language=detect_language(fi["path"]),
            ))

        logger.info(f"[GithubClient] Fetched {len(result)}/{len(file_list)} file contents")
        return result

    def fetch_repo_via_clone(self, repo_url: str, branch: str = "main") -> List[RepoFile]:
        """
        Fallback: clone the repo via git and read files from disk.
        Uses PAT for private repos if token is set.
        """
        tmp_dir = tempfile.mkdtemp(prefix="scanx_")
        clone_dir = os.path.join(tmp_dir, "repo")
        try:
            # Embed PAT in URL for private repos
            clone_url = repo_url
            if self.session.headers.get("Authorization"):
                token = self.session.headers["Authorization"].replace("token ", "")
                clone_url = repo_url.replace("https://", f"https://{token}@")
                logger.info("[GithubClient] Using PAT for private repo clone")

            cmd = [
                "git", "clone", "--depth", "1", "--branch", branch,
                "--single-branch", clone_url, clone_dir
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120, cwd=tmp_dir
            )
            if result.returncode != 0:
                raise RuntimeError(f"git clone failed: {result.stderr.strip()}")

            files = []
            for root, dirs, filenames in os.walk(clone_dir):
                # Skip hidden dirs and common non-source dirs
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS]
                for fname in filenames:
                    ext = "." + fname.rsplit(".", 1)[-1] if "." in fname else ""
                    if ext.lower() in SKIP_EXTENSIONS:
                        continue
                    fpath = os.path.join(root, fname)
                    rel_path = os.path.relpath(fpath, clone_dir)
                    size = os.path.getsize(fpath)
                    if size > MAX_FILE_SIZE:
                        continue
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                            content = fh.read()
                        if "\x00" in content:
                            continue
                        # Skip bundled/minified files based on content
                        if _should_skip_file(rel_path, fname, content):
                            continue
                        files.append(RepoFile(
                            path=rel_path,
                            name=fname,
                            size=size,
                            sha="",
                            content=content,
                            language=detect_language(rel_path),
                        ))
                    except Exception:
                        continue

            logger.info(f"[GithubClient] Cloned and read {len(files)} files")
            return files

        except Exception as e:
            logger.error(f"[GithubClient] Clone failed: {e}")
            raise
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
