"""
github_client.py — GitHub API client for fetching repository files.

Uses the GitHub REST API to list and read files from a repository.
Supports private repos via Personal Access Token (PAT).
"""

import re
import logging
import base64
from typing import List, Optional
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)

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

SKIP_NAME_PATTERNS = [
    r"^[a-z]+\.[a-f0-9]{6,}\.(js|css)$",
    r"^[a-z]+\.[a-f0-9]{6,}\.chunk\.(js|css)$",
    r"^vendors\.[a-f0-9]{6,}\.(js|css)$",
    r"^bundle\.[a-f0-9]{6,}\.(js|css)$",
    r"^app\.[a-f0-9]{6,}\.(js|css)$",
    r"^main\.[a-f0-9]{6,}\.(js|css)$",
]

MAX_FILE_SIZE = 500_000


@dataclass
class RepoFile:
    path: str
    name: str
    size: int
    sha: str
    content: str = ""
    language: str = ""


def parse_github_url(url: str) -> tuple:
    url = url.strip().rstrip("/")
    url = re.sub(r"\.git$", "", url)
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"^github\.com/", "", url)
    parts = url.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {url}. Expected format: owner/repo")
    return parts[0], parts[1]


def detect_language(path: str) -> str:
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

    def _check_rate_limit(self):
        """Check remaining API rate limit and warn if low."""
        try:
            resp = self.session.get(f"{self.base_url}/rate_limit")
            if resp.ok:
                remaining = resp.json().get("resources", {}).get("core", {}).get("remaining", 0)
                if remaining < 100:
                    logger.warning(f"[GithubClient] Low API rate limit: {remaining} remaining")
                return remaining
        except Exception:
            pass
        return None

    def get_repo_info(self, owner: str, repo: str) -> dict:
        resp = self.session.get(f"{self.base_url}/repos/{owner}/{repo}")
        resp.raise_for_status()
        return resp.json()

    def list_files(self, owner: str, repo: str, branch: str = "main") -> List[dict]:
        """
        Recursively list all files in a repo using the Git tree API.
        Returns flat list of file dicts with path, size, sha.
        """
        self._check_rate_limit()

        try:
            resp = self.session.get(
                f"{self.base_url}/repos/{owner}/{repo}/git/trees/{branch}",
                params={"recursive": "1"}
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else 0
            if status == 404:
                raise RuntimeError(
                    f"Repository not found: {owner}/{repo}. "
                    "Check the URL and ensure the repository exists. "
                    "If private, provide a PAT with 'repo' scope."
                )
            if status == 403:
                raise RuntimeError(
                    "Access denied. If this is a private repo, "
                    "provide a Personal Access Token with 'repo' scope."
                )
            if status == 401:
                raise RuntimeError("Invalid Personal Access Token. Check your PAT.")
            if status == 403:
                raise RuntimeError("Rate limited. Wait a few minutes and try again.")
            raise RuntimeError(f"GitHub API error: {e}")
        except Exception as e:
            # Try default branch if specified branch doesn't exist
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
        truncated = data.get("truncated", False)
        if truncated:
            logger.warning(f"[GithubClient] Tree truncated — large repo, some files may be missed")

        for item in data.get("tree", []):
            if item.get("type") != "blob":
                continue
            file_path = item["path"]
            parts = file_path.split("/")
            if any(p in SKIP_DIRS for p in parts):
                continue
            name = parts[-1]
            ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
            if ext.lower() in SKIP_EXTENSIONS:
                continue
            if item.get("size", 0) > MAX_FILE_SIZE:
                continue
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
                raw_resp = self.session.get(data["download_url"])
                raw_resp.raise_for_status()
                return raw_resp.text
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else 0
            if status == 403:
                logger.debug(f"[GithubClient] Rate limited fetching {file_path}, waiting...")
                import time
                time.sleep(5)
                try:
                    resp = self.session.get(
                        f"{self.base_url}/repos/{owner}/{repo}/contents/{file_path}"
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    if isinstance(data, dict) and data.get("content"):
                        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                except Exception:
                    pass
            logger.debug(f"[GithubClient] Could not fetch {file_path}: {e}")
        except Exception as e:
            logger.debug(f"[GithubClient] Could not fetch {file_path}: {e}")
        return None

    def fetch_repo_files(self, owner: str, repo: str, branch: str = "main") -> List[RepoFile]:
        """
        Fetch all readable files from a repo via GitHub API.
        Returns list of RepoFile with content populated.
        """
        file_list = self.list_files(owner, repo, branch=branch)
        result = []

        for fi in file_list:
            content = self.get_file_content(owner, repo, fi["path"])
            if content is None:
                continue
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
