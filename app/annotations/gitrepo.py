"""git CLI wrapper — the only module that knows git, GitLab or GitHub.
Reads work with any host. Writes open a review request: GitLab via push
options (no API call, no `api` scope), github.com via one REST call after
the push.

Auth: the token never appears in a URL, argv, on disk, or in logs. It is
handed to git as an HTTP header via GIT_CONFIG_* env (git >= 2.31), scoped
to the repo's scheme://host[:port]. That also makes git's stderr safe to
surface in errors — the URL carries no credentials (load_config rejects
URLs that do).
"""

import base64
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from email.utils import parseaddr
from pathlib import Path
from urllib.parse import quote, urlsplit

TIMEOUT = 300  # seconds per git call; a hung remote must not wedge the poller
LABEL = "ohmydb"  # on every MR/PR ohmydb opens
DESCRIPTION_MAX = 4000

# stderr fragments git/hosts emit on a rejected or missing credential
# (GitHub: "could not read Username"; GitLab: "HTTP Basic: Access denied").
_AUTH_FAILURE_MARKERS = ("could not read Username", "Authentication failed", "Access denied", "error: 401", "error: 403")


class GitError(RuntimeError):
    pass


def _env(url: str, token: str | None) -> dict[str, str]:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    parts = urlsplit(url)
    if token and parts.scheme == "https":
        basic = base64.b64encode(f"oauth2:{token}".encode()).decode()
        env |= {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": f"http.{parts.scheme}://{parts.netloc}/.extraHeader",
            "GIT_CONFIG_VALUE_0": f"Authorization: Basic {basic}",
        }
    return env


def _run(args: list[str], cwd: Path | None = None, url: str = "", token: str | None = None) -> subprocess.CompletedProcess:
    try:
        r = subprocess.run(
            ["git", *args], cwd=cwd, env=_env(url, token),
            capture_output=True, text=True, timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        raise GitError(f"git {args[0]} timed out after {TIMEOUT}s") from None
    if r.returncode != 0:
        stderr = r.stderr.strip()
        # git's wording for a rejected/missing token is cryptic ("could not
        # read Username ... terminal prompts disabled") — say what to check.
        hint = ""
        if any(m in stderr for m in _AUTH_FAILURE_MARKERS):
            state = "set" if token else "not set"
            hint = (f" — authentication failed: check OHMYDB_ANNOTATIONS_TOKEN ({state}) "
                    "is valid and has access to the repo (read; write for proposals/drift_mr)")
        raise GitError(f"git {args[0]} failed: {stderr}{hint}")
    return r


def clone(url: str, ref: str, dest: Path, token: str | None = None) -> str:
    """Shallow single-branch clone of `ref` into `dest`; returns HEAD sha."""
    _run(["clone", "--quiet", "--depth", "1", "--single-branch", "--branch", ref, "--", url, str(dest)],
         url=url, token=token)
    return rev_parse(dest, "HEAD")


def rev_parse(dest: Path, rev: str) -> str:
    return _run(["rev-parse", rev], cwd=dest).stdout.strip()


def remote_sha(url: str, ref: str, token: str | None = None) -> str | None:
    """Remote sha of branch `ref` (None if it doesn't exist), without fetching."""
    out = _run(["ls-remote", url, f"refs/heads/{ref}"], url=url, token=token).stdout
    return out.split()[0] if out.strip() else None


def ls_remote(url: str, ref: str, token: str | None = None) -> str:
    sha = remote_sha(url, ref, token)
    if sha is None:
        raise GitError(f"branch {ref!r} not found at {url}")
    return sha


def fetch(dest: Path, url: str, branch: str, token: str | None = None) -> str:
    """Shallow-fetch another branch into the clone; returns its sha (FETCH_HEAD)."""
    _run(["fetch", "--quiet", "--depth", "1", "origin", f"refs/heads/{branch}"], cwd=dest, url=url, token=token)
    return rev_parse(dest, "FETCH_HEAD")


def head_author_email(dest: Path, rev: str) -> str:
    # Shallow clones have no merge-base, so "who touched the branch" is
    # answered by its head commit's author, not by `git log A..B`.
    return _run(["log", "-1", "--format=%ae", rev], cwd=dest).stdout.strip()


def commit(dest: Path, message: str, author: str) -> str:
    """Stage everything and commit as `author` ("Name <email>"); returns sha."""
    name, email = parseaddr(author)
    _run(["add", "-A"], cwd=dest)
    _run(["-c", f"user.name={name}", "-c", f"user.email={email}", "commit", "--quiet", "-m", message], cwd=dest)
    return rev_parse(dest, "HEAD")


def publish(dest: Path, url: str, branch: str, expect: str, base: str, title: str, description: str,
            token: str | None = None) -> str | None:
    """Push HEAD to `branch` and open a merge/pull request into `base`;
    returns its URL (None if GitLab printed none). --force-with-lease=
    <ref>:<expect>: the branch must still be at `expect` ("" = must not
    exist yet), so a concurrent writer is never clobbered."""
    description = description.strip().replace("\r", "")[:DESCRIPTION_MAX]
    github = _github_repo(url)
    opts = [] if github else [arg for o in _gitlab_options(base, title, description) for arg in ("-o", o)]
    r = _run(["push", *opts, f"--force-with-lease=refs/heads/{branch}:{expect}",
              "origin", f"HEAD:refs/heads/{branch}"], cwd=dest, url=url, token=token)
    if github:
        return _github_pr(github, token, branch, base, title, description)
    return mr_url(r.stderr)


def _gitlab_options(base: str, title: str, description: str) -> list[str]:
    return [
        "merge_request.create",
        f"merge_request.target={base}",
        f"merge_request.title={title}",
        # Push option values can't carry a literal LF; GitLab expands "\n".
        "merge_request.description=" + description.replace("\n", "\\n"),
        f"merge_request.label={LABEL}",
        "merge_request.remove_source_branch",
    ]


def _github_repo(url: str) -> str | None:
    """owner/repo for a github.com remote, else None (= GitLab)."""
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != "github.com":
        return None
    return parts.path.strip("/").removesuffix(".git")


def _github_api(method: str, path: str, token: str | None, body: dict | None = None):
    req = urllib.request.Request(
        f"https://api.github.com{path}", method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise GitError(f"GitHub API {method} {path.split('?')[0]} failed: HTTP {e.code} {detail}") from None


def _github_pr(repo: str, token: str | None, branch: str, base: str, title: str, description: str) -> str:
    """Open a PR for the pushed branch, or reuse the open one (the rolling
    drift branch keeps its PR across force-pushes). Labeling is best effort."""
    try:
        pr = _github_api("POST", f"/repos/{repo}/pulls", token,
                         {"title": title, "head": branch, "base": base, "body": description})
    except GitError as e:
        if "HTTP 422" not in str(e):
            raise
        owner = repo.split("/")[0]
        open_prs = _github_api("GET", f"/repos/{repo}/pulls?state=open&head={quote(f'{owner}:{branch}')}", token)
        if not open_prs:
            raise
        pr = open_prs[0]
    try:
        _github_api("POST", f"/repos/{repo}/issues/{pr['number']}/labels", token, {"labels": [LABEL]})
    except GitError:
        pass
    return pr["html_url"]


def mr_url(text: str) -> str | None:
    """Best effort: GitLab echoes the MR link as `remote: ...` lines on push."""
    m = re.search(r"https?://\S+/-/merge_requests/\d+", text)
    return m.group(0) if m else None
