"""
Thin wrapper around the GitHub REST "contents" API, used to pull files out of
public repositories (zeldaret/oot, OoT-Randomizer) without a full `git clone`.

Anonymous requests are capped at 60/h; setting GITHUB_TOKEN (config.py) raises
that to 5000/h. In GitHub Actions, the workflow's own ambient token can be
passed through under that same env var name.
"""

import base64
import time

import httpx
from loguru import logger

from ocarina_nexus.config import GITHUB_TOKEN, USER_AGENT

API_URL = "https://api.github.com"


def _headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _get(url: str, params: dict | None = None) -> httpx.Response:
    with httpx.Client(headers=_headers(), timeout=30.0) as client:
        response = client.get(url, params=params)

    remaining = response.headers.get("X-RateLimit-Remaining")
    if remaining is not None and int(remaining) < 5:
        reset = response.headers.get("X-RateLimit-Reset")
        logger.warning(f"GitHub API quota nearly exhausted (remaining={remaining}, reset={reset})")

    if response.status_code == 403 and remaining == "0":
        reset_epoch = int(response.headers.get("X-RateLimit-Reset", "0"))
        wait_s = max(0, reset_epoch - int(time.time())) + 1
        logger.warning(f"GitHub API rate limit hit, sleeping {wait_s}s")
        time.sleep(wait_s)
        with httpx.Client(headers=_headers(), timeout=30.0) as client:
            response = client.get(url, params=params)

    response.raise_for_status()
    return response


def list_dir(owner: str, repo: str, path: str, ref: str = "main") -> list[dict]:
    """Lists entries of a directory. Each entry has name/path/type/download_url/size."""
    url = f"{API_URL}/repos/{owner}/{repo}/contents/{path}"
    data = _get(url, params={"ref": ref}).json()
    if isinstance(data, dict):
        # A single file path was given, not a directory.
        return [data]
    return data


def get_file_text(owner: str, repo: str, path: str, ref: str = "main") -> str:
    """Returns the decoded UTF-8 text content of a single file."""
    url = f"{API_URL}/repos/{owner}/{repo}/contents/{path}"
    data = _get(url, params={"ref": ref}).json()

    if data.get("content"):
        return base64.b64decode(data["content"]).decode("utf-8")

    # Files over ~1MB omit `content`; the contents API still gives us a raw URL.
    download_url = data.get("download_url")
    if not download_url:
        raise ValueError(f"No content and no download_url for {owner}/{repo}/{path}")
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60.0) as client:
        response = client.get(download_url)
        response.raise_for_status()
        return response.text


def list_tree_recursive(owner: str, repo: str, ref: str = "main") -> list[dict]:
    """Full recursive file tree of the repo at `ref` (path, sha, type, size)."""
    # Resolve ref -> commit sha -> tree sha is unnecessary: the git/trees API
    # accepts a branch name directly when recursive.
    url = f"{API_URL}/repos/{owner}/{repo}/git/trees/{ref}"
    data = _get(url, params={"recursive": "1"}).json()
    return data.get("tree", [])
